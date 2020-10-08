import itertools
import os
import cv2

from .frame_drawer import FrameDrawer
from .video_manager import VideoManager

get_your_config_from_env_var = os.environ.get('CONFIG_NAME', 'default_value_if_not_set')

'''
Sample code on usage for concurrent streams
Run from one level above video_utils (video_utils should be treated as a module, this file just acts as a crash course/demo: `python3 -m video_utils .`
'''
if __name__ == '__main__':
    frame_drawer = FrameDrawer()

    vidManager = VideoManager(video_feed_names=['File', 'RTSP'],
                              streams=['/data/datasets/drone/macritchie-reservoir.mp4',
                                       'rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mov'],
                              manual_video_fps=[None, None], queue_size=2, recording_dir='./video_utils/output',
                              reconnect_threshold_sec=5, max_height=1080, method='vlc')

    vidManager.start()
    print(f'{vidManager.get_all_videos_information()}')

    for frame_count in itertools.count():
        frame_of_each_video_feed = vidManager.read()  # frames is list of arrays from 0 - 255, dtype uint8
        for i, video_stream_information in enumerate(vidManager.videos):
            if len(frame_of_each_video_feed[i]) != 0:
                drawn_frame = frame_drawer.draw_detections(frame_of_each_video_feed[i],
                                                           [('test0', 0, (80, 80, 100, 60)),
                                                            ('test1', 0, (100, 100, 120, 80))])
                cv2.imshow(video_stream_information['video_feed_name'], drawn_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            cv2.destroyAllWindows()
            break

    vidManager.stop()
