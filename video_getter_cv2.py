import os
import time
from collections import deque
from datetime import datetime
from threading import Thread

import cv2


class VideoStream:
    """
    Class that continuously gets frames from a cv2 VideoCapture object
    with a dedicated thread.
    """

    def __init__(self, video_feed_name, src, manual_video_fps, queue_size=3, recording_dir=None,
                 reconnect_threshold_sec=20,
                 resize_fn=None,
                 frame_crop=None):
        self.video_feed_name = video_feed_name
        self.src = src
        self.stream = cv2.VideoCapture(self.src)
        self.reconnect_threshold_sec = reconnect_threshold_sec
        self.pauseTime = None
        self.stopped = True
        self.Q = deque(maxlen=queue_size)  # Maximum size of a deque or None if unbounded.
        self.resize_fn = resize_fn
        self.inited = False
        if (manual_video_fps == -1):
            self.manual_video_fps = None
        else:
            self.manual_video_fps = manual_video_fps
        self.vidInfo = {}
        self.recording_dir = recording_dir

        if self.recording_dir is not None:
            self.record_source_video = True
            if not os.path.isdir(self.recording_dir):
                os.makedirs(self.recording_dir)
        else:
            self.record_source_video = False
        if frame_crop is not None:
            assert len(frame_crop) == 4, 'Given FRAME CROP is invalid'
        self.frame_crop = frame_crop

    def init_src(self):
        try:
            self.stream = cv2.VideoCapture(self.src)
            if not self.manual_video_fps:
                self.fps = int(self.stream.get(cv2.CAP_PROP_FPS))
            else:
                self.fps = self.manual_video_fps
            # width and height returns 0 if stream not captured
            if self.frame_crop is None:
                self.vid_width = int(self.stream.get(3))
                self.vid_height = int(self.stream.get(4))
            else:
                l,t,r,b = self.frame_crop
                self.vid_width = r - l
                self.vid_height = b - t            

            self.vidInfo = {'video_feed_name': self.video_feed_name, 'height': self.vid_height, 'width': self.vid_width,
                            'manual_fps_inputted': self.manual_video_fps is not None,
                            'fps': self.fps, 'inited': False}

            self.out_vid = None

            if self.vid_width != 0:
                self.inited = True
                self.vidInfo['inited'] = True

            self.__init_src_recorder()

        except Exception as error:
            print('init stream {} error: {}'.format(self.video_feed_name, error))

    def __init_src_recorder(self):
        if self.record_source_video and self.inited:
            now = datetime.now()
            day = now.strftime("%Y_%m_%d_%H-%M-%S")
            out_vid_fp = os.path.join(
                self.recording_dir, 'orig_{}_{}.avi'.format(self.video_feed_name, day))
            self.out_vid = cv2.VideoWriter(out_vid_fp, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'), int(
                self.fps), (self.vid_width, self.vid_height))

    def start(self):
        if not self.inited:
            self.init_src()
    
        self.stopped = False

        t = Thread(target=self.get, args=())
        t.start()

        print('start video streaming for {}'.format(self.video_feed_name))
        return self

    def reconnect_start(self):
        s = Thread(target=self.reconnect, args=())
        s.start()
        return self

    def get(self):
        while not self.stopped:
            try:
                # print('getting video' + str(time.time()))
                grabbed, frame = self.stream.read()

                if grabbed:
                    if self.frame_crop is not None:
                        l,t,r,b = self.frame_crop
                        frame = frame[t:b,l:r]

                    self.Q.appendleft(frame)

                    if self.record_source_video:
                        try:
                            self.out_vid.write(frame)
                        except Exception as e:
                            pass

                    time.sleep(1 / self.fps)

            except Exception as e:
                print('stream grab {} error: {}'.format(self.video_feed_name, e))
                grabbed = False

            if not grabbed:
                if self.reconnect_threshold_sec > 0:
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
                else:
                    print(f'No frames for {self.video_feed_name}. Not reconnecting. Stopping..')
                    self.stop()
                    break

            self.pauseTime = None

    def read(self):
        if self.more():
            self.currentFrame = self.Q.pop()
        if self.resize_fn:
            self.currentFrame = self.resize_fn(self.currentFrame)
        return self.currentFrame

    def more(self):
        return bool(self.Q)

    def stop(self):
        if not self.stopped:
            self.stopped = True
            time.sleep(0.1)

            if self.stream:
                self.stream.release()

            if self.more():
                self.Q.clear()

            if self.out_vid:
                self.out_vid.release()

            print('stop video streaming for {}'.format(self.video_feed_name))

    def reconnect(self):
        print('Reconnecting')
        if self.stream:
            self.stream.release()

        if self.more():
            self.Q.clear()

        while not self.stream.isOpened():
            print(str(datetime.now()), 'Reconnecting to', self.video_feed_name)
            self.stream = cv2.VideoCapture(self.src)
        if not self.stream.isOpened():
            return ('error opening {}'.format(self.video_feed_name))

        if not self.inited:
            self.init_src()

        print('VideoStream for {} initialised!'.format(self.video_feed_name))
        self.pauseTime = None
        self.start()
