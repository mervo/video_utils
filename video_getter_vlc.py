import time

import cv2
import vlc

import video_getter_cv2


class VideoStream(video_getter_cv2.VideoStream):
    """
    Class that uses vlc instead of cv2 to continuously get frames with a dedicated thread as a workaround for artifacts.
    """

    def __init__(self, video_feed_name, src, is_video_file=True, queue_size=3, recording_dir=None,
                 reconnect_threshold_sec=20,
                 resize_fn=None):
        video_getter_cv2.VideoStream.__init__(self, video_feed_name, src, is_video_file, queue_size, recording_dir,
                                              reconnect_threshold_sec,
                                              resize_fn)

        self.fixed_png_path = 'vlc_frame_{}.png'.format(video_feed_name)
        self.stream = cv2.VideoCapture(self.src)
        self.vlc_instance = vlc.Instance('--vout=dummy --aout=dummy')
        self.vlc_player = self.vlc_instance.media_player_new()
        self.vlc_player.set_mrl(self.src)

    def get(self):
        self.vlc_player.play()
        while not self.stopped:
            try:
                # print('getting video' + str(time.time()))
                res = self.vlc_player.video_take_snapshot(0, self.fixed_png_path, 0, 0)
                grabbed = (res >= 0)

                if grabbed:
                    frame = cv2.imread(self.fixed_png_path)
                    self.Q.appendleft(frame)

                    if self.record_tracks:
                        try:
                            self.out_vid.write(frame)
                        except Exception as e:
                            pass

                    if self.is_video_file:
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

            # if self.stream:
            # self.stream.release()

            if self.more():
                self.Q.clear()

            if self.vlc_player:
                self.vlc_player.stop()
                self.vlc_player.release()
                self.vlc_instance.release()

            if self.record_tracks and self.out_vid:
                self.out_vid.release()

            print('stop video streaming for {}'.format(self.video_feed_name))

    def reconnect(self):
        print('Reconnecting')

        if self.more():
            self.Q.clear()

        if self.vlc_player:
            self.vlc_player.stop()
            self.vlc_player.release()

        self.vlc_player = self.vlc_instance.media_player_new()
        self.vlc_player.set_mrl(self.src)

        if self.record_tracks and not self.inited:
            self.init_src()

        print('VideoStream for {} initialised!'.format(self.video_feed_name))
        self.pauseTime = None
        self.start()
