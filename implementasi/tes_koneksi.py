import pydobot

# Change to your actual port (might be COM6, COM7, etc...)
device = pydobot.Dobot(port="COM3", verbose=False)


def move_cal():
    # Function to move calibration (bottom left and top right)
    device.move_to(250, 0, 0, 0, mode=0, wait=True)
    device.move_to(284, 125, -50, 0, mode=0, wait=True)
    device.move_to(165, -130, -50, 0, mode=0, wait=True)
    device.move_to(250, 0, 0, 0, mode=0, wait=True)

# For homing (recomended for accurate coordinate (its kinda like calibration))
# device.home()

# Call the move_cal function for calibration
# move_cal()
