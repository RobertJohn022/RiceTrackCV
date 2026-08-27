import cv2
import numpy

lcc = cv2.imread('assets/lcc.jpg')          # PANELS
rice1 = cv2.imread('assets/pixel1.png')     # RICE PIC TEST

# Make window bigger (400,400) but keep original resolution (32,32)
bigRice1 = cv2.resize(rice1, (400, 400), interpolation=cv2.INTER_NEAREST)
# winPix1 = "WinPix2"
cv2.imshow('riceWindow', bigRice1)

print("light = ", rice1[31][0])
print("dark = ", rice1[31][1])

# PANEL 2
pan2 = lcc[60:100, 60:100]                          # = get specific region [ymin:ymax, xmin:xmax]
avg2 = cv2.mean(pan2)                               # = compute average (mean)
hsv_pan2 = cv2.cvtColor(pan2, cv2.COLOR_BGR2HSV)    # = convert BGR to HSV
avg_hue2 = cv2.mean(hsv_pan2) [0]                   # = compute avg hue[0]
bigPan2 = cv2.resize(pan2, (200, 200), interpolation=cv2.INTER_NEAREST)

b2, g2, r2 = avg2[:3]
hueChannel = hsv_pan2[:, :, 0]
minHue, maxHue, _, _ = cv2.minMaxLoc(hueChannel)
print("\nPANEL 2:")
print(f"  Avg BGR = B: {b2:.2f}, G: {g2:.2f}, R: {r2:.2f}")
print(f"  Avg hue: {avg_hue2:.2f}, Min Hue: {minHue}, MaxHue: {maxHue}")

# PANEL 3
pan3 = lcc[60:100, 200:240]
avg3 = cv2.mean(pan3)
hsv_pan3 = cv2.cvtColor(pan3, cv2.COLOR_BGR2HSV)
avg_hue3 = cv2.mean(hsv_pan3) [0]
bigPan3 = cv2.resize(pan3, (200, 200), interpolation=cv2.INTER_NEAREST)

b3, g3, r3 = avg3[:3]
hueChannel = hsv_pan3[:, :, 0]
minHue, maxHue, _, _ = cv2.minMaxLoc(hueChannel)
print("\nPANEL 3:")
print(f"  Avg BGR = B: {b3:.2f}, G: {g3:.2f}, R: {r3:.2f}")
print(f"  Avg hue: {avg_hue3:.2f}, Min Hue: {minHue}, MaxHue: {maxHue}")

# PANEL 4
pan4 = lcc[60:100, 340:380]
avg4 = cv2.mean(pan4)
hsv_pan4 = cv2.cvtColor(pan4, cv2.COLOR_BGR2HSV)
avg_hue4 = cv2.mean(hsv_pan4) [0]
bigPan4 = cv2.resize(pan4, (200, 200), interpolation=cv2.INTER_NEAREST)

b4, g4, r4 = avg4[:3]
hueChannel = hsv_pan4[:, :, 0]
minHue, maxHue, _, _ = cv2.minMaxLoc(hueChannel)
print("\nPANEL 4:")
print(f"  Avg Pan4 BGR: B={b4:.2f}, G={g4:.2f}, R={r4:.2f}")
print(f"  Avg hue: {avg_hue4:.2f}, Min Hue: {minHue}, MaxHue: {maxHue}")

# PANEL 5
pan5 = lcc[60:100, 500:540]
avg5 = cv2.mean(pan5)
hsv_pan5 = cv2.cvtColor(pan5, cv2.COLOR_BGR2HSV)
avg_hue5 = cv2.mean(hsv_pan5) [0]
bigPan5 = cv2.resize(pan5, (200, 200), interpolation=cv2.INTER_NEAREST)

b5, g5, r5 = avg5[:3]
hueChannel = hsv_pan5[:, :, 0]
minHue, maxHue, _, _ = cv2.minMaxLoc(hueChannel)
print("\nPANEL 5:")
print(f"  Avg Pan5 BGR: B={b5:.2f}, G={g5:.2f}, R={r5:.2f}")
print(f"  Avg hue: {avg_hue5:.2f}, Min Hue: {minHue}, MaxHue: {maxHue}")

# DISPLAY
oneWindow = numpy.concatenate((bigPan2, bigPan3, bigPan4, bigPan5), axis=1)
cv2.imshow('oneWindow', oneWindow)
# cv2.imshow('oneWindow', bigPan2)
# panel2()

cv2.waitKey(0)
cv2.destroyAllWindows()

# OpenCV how to display average hue for a selected region of an image like this: panel = img[60:100, 200:240]