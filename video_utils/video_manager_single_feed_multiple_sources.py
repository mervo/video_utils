from video_utils import video_manager

class VideoManager(video_manager.VideoManager):
    def __init__(self, source_type, stream, manual_video_fps, rectangle_crops, queue_size=3, recording_dir=None,
                 reconnect_threshold_sec=20,
                 max_height=1080,
                 method='cv2'):
        """VideoManager that helps with multiple concurrent video streams

        Args:
            source_type (str): string for identifying whether it is a stream or a video: 'usb', 'file', 'rtsp', 'http/https'
            stream(str) : file path or rtsp stream
            manual_video_fps (int): fps of stream, -1 if fps information available from video source
            rectangle_crops(list): list of (x, y, w, h) to crop as individual video feeds
            (x,y) = the top-left coordinate of the rectangle
            (w,h) = width and height
            queue_size (int): No. of frames to buffer in memory to prevent blocking I/O operations (https://www.pyimagesearch.com/2017/02/06/faster-video-file-fps-with-cv2-videocapture-and-opencv/)
            recording_dir (str): Path to folder to record source video, None to disable recording.
            reconnect_threshold_sec (int): Min seconds between reconnection attempts, set higher for vlc to give it time to connect
            max_height(int): Max height of video in px
            method (str): 'cv2' or 'vlc', 'vlc' is slower but more robust to artifacting
        """

        self.max_height = int(max_height)
        self.num_vid_streams = len(rectangle_crops)
        self.rectangle_crops = rectangle_crops
        self.stopped = True

        self.videos = []

        if (method == 'cv2'):
            from .video_getter_cv2 import VideoStream
        elif (method == 'vlc'):
            from .video_getter_vlc import VideoStream
        else:
            from .video_getter_cv2 import VideoStream

        stream = VideoStream('MASTER_STREAM', source_type, stream, manual_video_fps=int(manual_video_fps),
                             queue_size=int(queue_size), recording_dir=recording_dir,
                             reconnect_threshold_sec=int(reconnect_threshold_sec))

        self.videos.append({'video_feed_name': 'MASTER_STREAM', 'stream': stream})

    def read(self):
        frames = []

        for vid in self.videos:
            if not vid['stream'].more():  # Frame not here yet
                frames = ([[]] * len(self.rectangle_crops))  # Maintain frames size(frame from each video feed)
            else:
                frame = vid['stream'].read()
                for cur_rectangle_crop in self.rectangle_crops:
                    x, y, w, h = cur_rectangle_crop
                    frames.append(frame[y:y + h, x:x + w])

        return frames
