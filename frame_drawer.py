import cv2
import copy

RED = (0, 0, 255)
LESS_RED = (0, 20, 100)
TEAL = (148, 184, 0)


class FrameDrawer(object):
    def __init__(self, color=(255, 255, 255), font=cv2.FONT_HERSHEY_COMPLEX):
        self.color = color

        self.font = font
        self.fontScale = 1
        self.fontThickness = 2

        self.rectangleThickness = 2

    def draw_detections(self, source_frame, detections, color=None):
        """
        Args:
            source_frame: input frame
            detections: list of detection tuples: [(class, confidence , (l, t, r, b)) ...]
            (left, top, right, bottom)
            color: color of rectangle and text

        Returns:
            new frame with bounding boxes and classes(if any)
        """

        if detections is None or len(detections) == 0:
            return source_frame
        if color is None:
            color = self.color
        frame_deep_copied = copy.deepcopy(source_frame)

        for cur_detection in detections:
            text = f'{cur_detection[0]}: {cur_detection[1] * 100:0.2f}%'
            l = cur_detection[2][0]
            t = cur_detection[2][1]
            r = cur_detection[2][2]
            b = cur_detection[2][3]
            cv2.rectangle(frame_deep_copied, (l, t), (r, b), color, self.rectangleThickness)
            cv2.putText(frame_deep_copied,
                        text,
                        (l + 5, b - 10),
                        self.font, self.fontScale, color, self.fontThickness)
        return frame_deep_copied
