import numpy as np


class VideoManager:
    def __init__(self, video_feed_names, streams, queue_size=5, recording_dir=None, reconnect_threshold_sec=20, max_height=720,
                 is_video_file=True, method='cv2'):
        self.max_height = max_height
        self.num_vid_streams = len(streams)
        self.stopped = True

        assert len(streams) == len(video_feed_names), 'streams and camNames should be the same length'
        self.videos = []

        if (method == 'cv2'):
            from video_getter_cv2 import VideoStream
        elif (method == 'vlc'):
            from video_getter_vlc import VideoStream

        for i, camName in enumerate(video_feed_names):
            stream = VideoStream(camName, streams[i], queue_size=queue_size, recording_dir=recording_dir,
                                 reconnect_threshold_sec=reconnect_threshold_sec, is_video_file=is_video_file)

            self.videos.append({'camName': camName, 'stream': stream})

    # def _resize(self, frame):
    # 	height, width = frame.shape[:2]
    # 	if height != self.resize_height or width != self.resize_width:
    # 		# print("Resizing from {} to {}".format((height, width), (resize_height, resize_width)))
    # 		frame = cv2.resize(frame, (self.resize_width, self.resize_height))
    # 	return frame

    def start(self):
        if self.stopped:
            # print('vid manager start')
            for vid in self.videos:
                vid['stream'].start()

            self.stopped = False

    def stop(self):
        if not self.stopped:
            # print('vid manager stop')
            self.stopped = True
            # time.sleep(1)

            for vid in self.videos:
                vid['stream'].stop()

    def update_info(self):
        for i, vid in enumerate(self.videos):
            vid['info'] = vid['stream'].vidInfo

    def getAllInfo(self):
        all_info = []
        for vid in self.videos:
            all_info.append(vid['stream'].vidInfo)
        return all_info

    def read(self):
        frames = []

        for vid in self.videos:
            if not vid['stream'].more():  # Frame not here yet
                frames.append([])  # Maintain frames size(frame from each video feed)
            else:
                frame = vid['stream'].read()
                frames.append(frame)

        return frames
