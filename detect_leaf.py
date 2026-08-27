import cv2
import numpy

rice1 = cv2.imread('assets/pixel1.png')     # RICE PIC TEST

bigRice1 = cv2.resize(rice1, (400, 400), interpolation=cv2.INTER_NEAREST)
cv2.imshow('riceWindow', bigRice1)

# MIN BGR (PAN 2) = (26, 44, 35)
# MAX BGR (PAN 5) = (24, 121, 104)
# MIN HUE = 35.0
# MAX HUE = 53.0

cv2.waitKey(0)
cv2.destroyAllWindows()