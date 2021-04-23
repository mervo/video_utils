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

    def __init__(self, video_feed_name, source_type, src, manual_video_fps, queue_size=3, recording_dir=None,
                 reconnect_threshold_sec=20,
                 do_reconnect=True,
                 resize_fn=None,
                 frame_crop=None,
                 rtsp_tcp=True,
                 logger=None):
        video_getter_cv2.VideoStream.__init__(self, video_feed_name, source_type, src, manual_video_fps, 
                        queue_size=queue_size, 
                        recording_dir=recording_dir,
                        reconnect_threshold_sec=reconnect_threshold_sec,
                        do_reconnect=do_reconnect,
                        resize_fn=resize_fn,
                        frame_crop=frame_crop,
                        rtsp_tcp=rtsp_tcp,
                        logger=logger)

        self.fixed_png_path = 'temp_vlc_frame_{}.png'.format(video_feed_name)
        vlc_flags = '--vout=dummy --aout=dummy'
        if rtsp_tcp:
            vlc_flags += ' --rtsp-tcp'
        self.vlc_instance = vlc.Instance(vlc_flags)
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
        # Known Issue: This needs to be called again after "play()" for the video feed to start coming in, unable to figure out why
        self.vlc_player = self.vlc_instance.media_player_new()
        self.vlc_player.set_mrl(self.src)
        self.vlc_player.play()

        while not self.stopped:
            try:
                res = self.vlc_player.video_take_snapshot(0, self.fixed_png_path, 0, 0)
                grabbed = (res >= 0)

                if grabbed:
                    frame = cv2.imread(self.fixed_png_path)
                    if self.frame_crop is not None:
                        l,t,r,b = self.frame_crop
                        frame = frame[t:b,l:r]

                    self.Q.appendleft(frame)

                    time.sleep(1 / self.fps)

            except Exception as e:
                self.logger.warning('Stream {} grab error: {}'.format(self.video_feed_name, e))
                grabbed = False

            if not grabbed:
                if self.pauseTime is None:
                    self.pauseTime = time.time()
                    self.printTime = time.time()
                    self.logger.info('No frames for {}, starting {:0.1f}sec countdown.'. \
                          format(self.video_feed_name, self.reconnect_threshold_sec))
                time_since_pause = time.time() - self.pauseTime
                countdown_time = self.reconnect_threshold_sec - time_since_pause
                time_since_print = time.time() - self.printTime
                if time_since_print > 1 and countdown_time >= 0:  # prints only every 1 sec
                    self.logger.debug(f'No frames for {self.video_feed_name}, countdown: {countdown_time:0.1f}sec')
                    self.printTime = time.time()

                if countdown_time <= 0 :
                    if self.do_reconnect:
                        self.reconnect_start()
                        break
                    elif not self.more():
                        self.logger.info(f'Not reconnecting. Stopping..')
                        self.stop()
                        break
                    else:
                        time.sleep(1)
                        self.logger.debug(f'Countdown reached but still have unconsumed frames in deque: {len(self.Q)}')
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

            self.logger.info('Stopped video streaming for {}'.format(self.video_feed_name))

    def reconnect(self):
        self.logger.info(f'Reconnecting to {self.video_feed_name}...')
        if self.more():
            self.Q.clear()

        if self.vlc_player:
            self.vlc_player.stop()
            self.vlc_player.release()

        # Known Issue: This needs to be called again after "play()" for the video feed to start coming in, unable to figure out why
        self.vlc_player = self.vlc_instance.media_player_new()
        self.vlc_player.set_mrl(self.src)

        if not self.inited:
            self.init_src()

        self.logger.info('VideoStream for {} initialised!'.format(self.video_feed_name))
        self.pauseTime = None
        self.start()

    def get_frame_time(self, clock, do_set_start_time=False):
        """
        Parameters
        ----------
        clock : utils.clock.Clock object
            Clock object
        do_set_start_time : bool 
            Flag to determine whether to get 'current' time in video/stream, or present day time.

        Returns
        ----------
         - If do_set_start_time is True, returns time elapsed since start of video in milliseconds
         - Else, returns current unix time, in milliseconds
         """      
        if do_set_start_time:
            return self.vlc_player.get_time()
        else: 
            return int(1000 * clock.get_now_SGT_unixts())

