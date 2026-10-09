import cv2
import numpy

lcc = cv2.imread('images/lcc.jpg')          # PANELS
rice1 = cv2.imread('images/pixel1.png')     # RICE PIC TEST

# Make window bigger (400,400) but keep original resolution (32,32)
# bigRice1 = cv2.resize(rice1, (400, 400), interpolation=cv2.INTER_NEAREST)
# cv2.imshow('riceWindow', bigRice1)

# print("light = ", rice1[31][0])
# print("dark = ", rice1[31][1])

count = 2
# [minH:maxH - minW:maxW]
pan2 = lcc[10:240, 50:150]    
pan3 = lcc[10:240, 200:300]
pan4 = lcc[10:240, 340:440]
pan5 = lcc[10:240, 480:580]

panel_range = [pan2, pan3, pan4, pan5]
panel_imgs = []

def getHues(panRange):
    avg = cv2.mean(panRange)
    hsv_pan = cv2.cvtColor(panRange, cv2.COLOR_BGR2HSV)
    avg_hue = cv2.mean(hsv_pan) [0]
    bigPan = cv2.resize(panRange, (200, 480), interpolation=cv2.INTER_NEAREST)  # W x H (100,240)*2
    panel_imgs.append(bigPan)

    b, g, r = avg[:3]
    hueChannel = hsv_pan[:, :, 0]
    minHue, maxHue, _, _ = cv2.minMaxLoc(hueChannel)
    print("\nPANEL ", count, ": ")
    print(f"  Avg BGR = B: {b:.2f}, G: {g:.2f}, R: {r:.2f}")
    print(f"  Avg hue: {avg_hue:.2f}, Min Hue: {minHue}, MaxHue: {maxHue}")
    displayPanel()

def displayPanel():
    oneWindow = numpy.concatenate((panel_imgs), axis=1)
    cv2.imshow('oneWindow', oneWindow)

for i in panel_range:
    getHues(i)
    count += 1

cv2.waitKey(0)
cv2.destroyAllWindows()
