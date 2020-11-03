from pathlib import Path

class VideoManager:
    def __init__(self, video_feed_names, streams, manual_video_fps, queue_size=3, recording_dir=None,
                 reconnect_threshold_sec=20,
                 max_height=None,
                 method='cv2',
                 frame_crop=None,
                 rtsp_tcp=True):
        """VideoManager that helps with multiple concurrent video streams

        Args:
            video_feed_names (list): List of human readable strings for ease of identifying video source
            streams (list): List of strings of file paths or rtsp streams
            manual_video_fps (list): List of fps(int) for each stream, -1 if fps information available from video source
            queue_size (int or None): No. of frames to buffer in memory to prevent blocking I/O operations (https://www.pyimagesearch.com/2017/02/06/faster-video-file-fps-with-cv2-videocapture-and-opencv/). Set to None to prevent dropping any frames (only do this for video files)
            recording_dir (str): Path to folder to record source video, None to disable recording.
            reconnect_threshold_sec (int): Min seconds between reconnection attempts, set higher for vlc to give it time to connect
            max_height(int): Max height of video in px
            method (str): 'cv2' or 'vlc', 'vlc' is slower but more robust to artifacting
            frame_crop (list): LTRB coordinates for frame cropping 
            rtsp_tcp (bool): Only for 'vlc' method. Default is True. If rtsp stream is UDP, then setting to False will remove "--rtsp-tcp" flag from vlc command.  
        """

        # self.max_height = int(max_height)
        self.num_vid_streams = len(streams)
        self.stopped = True

        assert len(streams) == len(video_feed_names), 'streams and camNames should be the same length'
        self.videos = []

        if (method == 'cv2'):
            from .video_getter_cv2 import VideoStream
        elif (method == 'vlc'):
            from .video_getter_vlc import VideoStream
        else:
            from .video_getter_cv2 import VideoStream

        for i, video_feed_name in enumerate(video_feed_names):
            stream = VideoStream(video_feed_name, streams[i], 
                                manual_video_fps=int(manual_video_fps[i]),
                                queue_size=queue_size, recording_dir=recording_dir,
                                reconnect_threshold_sec=int(reconnect_threshold_sec),
                                frame_crop=frame_crop,
                                rtsp_tcp=rtsp_tcp)

            self.videos.append({'video_feed_name': video_feed_name, 'stream': stream})

    @classmethod
    def from_list_file(cls, list_file, **kwargs):
        '''
        Args:
        - list_file (str): Path to a txt file containing a list of camera info. Each row is <cam name>,<cam url>,<fps if applicable>. <cam url> is defined as "<source type>:<path>", where source type can be like "rtsp", "usb", "file" (see `cameras-example.list` for example)

        Note:
        - if all streams are files and queue_size is not given as an argument in kwargs, then queue_size will be set to None instead of default value of 3 as we do not want to drop any frames.

        '''
        video_feed_names = []
        streams = []
        manual_video_fps = []
        pure_files_only = True
        with open(list_file, 'r') as f:
            for l in f.readlines():
                l = l.strip()
                if l.startswith('#'):
                    continue
                splits = l.split(',')
                video_feed_names.append(splits[0])
                url = splits[1]
                sourcetype, path = url.split(':', 1)
                if sourcetype == 'usb':
                    video_path = int(path)
                    pure_files_only = False
                elif sourcetype == 'file':
                    video_path = path
                    assert Path(video_path).is_file(),f'{video_path} is defined as file but it does not exist!'
                else:
                    assert sourcetype == 'rtsp' or sourcetype == 'http' or sourcetype == 'https',f'Source type given of {sourcetype} is not supported' # Unsure if there are other types of video network stream protocols/  
                    video_path = url
                    pure_files_only = False
                streams.append(video_path)
                
                if len(splits) == 3:
                    fps = float(splits[2])
                    # fps = int(splits[2])
                else:
                    fps = -1
                manual_video_fps.append(fps)
        if pure_files_only and 'queue_size' not in kwargs:
            kwargs['queue_size'] = None

        return cls(video_feed_names, streams, manual_video_fps, **kwargs)

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

    def check_all_stopped(self):
        return all(vid['stream'].stopped for vid in self.videos)

    def check_any_stopped(self):
        return all(vid['stream'].stopped for vid in self.videos)

    def update_info(self):
        for i, vid in enumerate(self.videos):
            vid['info'] = vid['stream'].vidInfo

    def get_all_videos_information(self):
        all_info = []
        for vid in self.videos:
            if not vid['stream'].inited:
                vid['stream'].init_src()
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
