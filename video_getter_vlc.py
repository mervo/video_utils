from datetime import datetime
import os
import time

import cv2
import vlc

from . import video_getter_cv2


class VideoStream(video_getter_cv2.VideoStream):
    """
    Class that uses vlc instead of cv2 to continuously get frames with a dedicated thread as a workaround for artifacts.
    """

    def __init__(self, video_feed_name, src, manual_video_fps, queue_size=3, recording_dir=None,
                 reconnect_threshold_sec=20,
                 resize_fn=None):
        video_getter_cv2.VideoStream.__init__(self, video_feed_name, src, manual_video_fps, queue_size, recording_dir,
                                              reconnect_threshold_sec,
                                              resize_fn)

        self.fixed_png_path = 'temp_vlc_frame_{}.png'.format(video_feed_name)
        self.vlc_instance = vlc.Instance('--vout=dummy --aout=dummy')
        self.vlc_player = self.vlc_instance.media_player_new()

        if self.record_source_video:
            now = datetime.now()
            day = now.strftime("%Y_%m_%d_%H-%M-%S")
            out_vid_fp = os.path.join(
                self.recording_dir, 'orig_{}_{}.mp4'.format(self.video_feed_name, day))
            self.vlc_media = self.vlc_instance.media_new(self.src,
                                                         f'sout=#duplicate{{dst=display,dst=std{{access=file,mux=ts,dst={out_vid_fp}}}')
        else:
            self.vlc_media = self.vlc_instance.media_new(self.src)

        self.vlc_player.set_media(self.vlc_media)

    def __init_src_recorder(self):
        # disable video_getter_cv2 cv2.VideoWriter
        pass

    def get(self):
        self.vlc_player.play()
        while not self.stopped:
            try:
                res = self.vlc_player.video_take_snapshot(0, self.fixed_png_path, 0, 0)
                grabbed = (res >= 0)

                if grabbed:
                    frame = cv2.imread(self.fixed_png_path)
                    self.Q.appendleft(frame)

                    time.sleep(1 / self.fps)

            except Exception as e:
                print('stream grab error:{}'.format(e))
                grabbed = False

            if not grabbed:
                if self.pauseTime is None:
                    self.pauseTime = time.time()
                    self.printTime = time.time()
                    print('No frames for {}, starting {:0.1f}sec countdown to reconnect.'. \
                          format(self.video_feed_name, self.reconnect_threshold_sec))
                time_since_pause = time.time() - self.pauseTime
                time_since_print = time.time() - self.printTime
                if time_since_print > 1:  # prints only every 1 sec
                    print('No frames for {}, reconnect starting in {:0.1f}sec'. \
                          format(self.video_feed_name, self.reconnect_threshold_sec - time_since_pause))
                    self.printTime = time.time()

                if time_since_pause > self.reconnect_threshold_sec:
                    self.reconnect_start()
                    break
                continue

            self.pauseTime = None

    def stop(self):
        if not self.stopped:
            self.stopped = True
            time.sleep(0.1)

            if self.more():
                self.Q.clear()

            if self.vlc_player:
                self.vlc_player.stop()
                self.vlc_player.release()
                self.vlc_instance.release()

            print('stop video streaming for {}'.format(self.video_feed_name))

    def reconnect(self):
        print('Reconnecting...')

        if self.more():
            self.Q.clear()

        if self.vlc_player:
            self.vlc_player.stop()
            self.vlc_player.release()

        self.vlc_player = self.vlc_instance.media_player_new()
        self.vlc_player.set_mrl(self.src)

        if not self.inited:
            self.init_src()

        print('VideoStream for {} initialised!'.format(self.video_feed_name))
        self.pauseTime = None
        self.start()
