import itertools
import os
import cv2

from video_utils.frame_drawer import FrameDrawer

get_your_config_from_env_var = os.environ.get('CONFIG_NAME', 'default_value_if_not_set')

# comma separated strings
video_feed_names = os.environ.get('VIDEO_FEED_NAMES',
                                  'FILE1,RTSP2')
streams = os.environ.get('STREAMS',
                         '/data/datasets/drone/macritchie-reservoir.mp4,rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mov')
manual_video_fps = os.environ.get('MANUAL_VIDEO_FPS', '-1,-1')  # -1 to try to read from video stream metadata
source_types = os.environ.get('SOURCE_TYPES', 'file,rtsp')

queue_size = int(os.environ.get('QUEUE_SIZE', 2))
recording_dir = os.environ.get('RECORDING_DIR', None)
reconnect_threshold_sec = int(os.environ.get('RECONNECT_THRESHOLD_SEC', 5))
max_height = int(os.environ.get('MAX_HEIGHT', 1080))
method = os.environ.get('METHOD', 'cv2')

'''
Sample code on usage for concurrent streams
Run from one level above video_utils (video_utils should be treated as a module, this file just acts as a crash course/demo: `python3 -m video_utils .`
'''


def one_video_manager_to_many_source():
    frame_drawer = FrameDrawer()
    from video_utils.video_manager import VideoManager

    vidManager = VideoManager(video_feed_names=video_feed_names.split(','),
                              streams=streams.split(','), source_types=source_types.split(','),
                              manual_video_fps=manual_video_fps.split(','), queue_size=queue_size,
                              recording_dir=recording_dir,
                              reconnect_threshold_sec=reconnect_threshold_sec, max_height=max_height, method=method)

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


def one_video_manager_to_one_source():
    frame_drawer = FrameDrawer()
    from video_utils.video_manager_single_feed_multiple_sources import VideoManager

    vidManager = VideoManager(source_type='rtsp',
                              stream='rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mov',
                              manual_video_fps=-1,
                              rectangle_crops=[(0, 0, 60, 160), (80, 0, 60, 160), (160, 0, 60, 160)],
                              queue_size=queue_size,
                              recording_dir=recording_dir,
                              reconnect_threshold_sec=reconnect_threshold_sec, max_height=max_height, method=method)

    vidManager.start()
    print(f'{vidManager.get_all_videos_information()}')

    for frame_count in itertools.count():
        frame_of_each_video_feed = vidManager.read()  # frames is list of arrays from 0 - 255, dtype uint8
        for i in range(vidManager.num_vid_streams):
            if len(frame_of_each_video_feed[i]) != 0:
                drawn_frame = frame_drawer.draw_detections(frame_of_each_video_feed[i],
                                                           [('test0', 0, (80, 80, 100, 60)),
                                                            ('test1', 0, (100, 100, 120, 80))])
                cv2.imshow(str(i), drawn_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            cv2.destroyAllWindows()
            break

    vidManager.stop()


if __name__ == '__main__':
    one_video_manager_to_many_source()
    # one_video_manager_to_one_source()
