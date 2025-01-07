import datetime
import torch
import cv2
from flask import current_app
def get_current_time():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')




