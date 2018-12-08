'''
Main program
@Author: David Vu

To execute simply run:
main.py

To input new user:
main.py --mode "input"

'''
import requests
import cv2
from align_custom import AlignCustom
from face_feature import FaceFeature
from mtcnn_detect import MTCNNDetect
from tf_graph import FaceRecGraph
import argparse
import sys
import json
import time
import numpy as np

TIMEOUT = 10 #10 seconds

def main(args):
    mode = args.mode
    if(mode == "camera"):
        camera_recog()
    elif mode == "input":
        create_manual_data();
    else:
        raise ValueError("Unimplemented mode")
'''
Description:
Images from Video Capture -> detect faces' regions -> crop those faces and align them
    -> each cropped face is categorized in 3 types: Center, Left, Right
    -> Extract 128D vectors( face features)
    -> Search for matching subjects in the dataset based on the types of face positions.
    -> The preexisitng face 128D vector with the shortest distance to the 128D vector of the face on screen is most likely a match
    (Distance threshold is 0.6, percentage threshold is 70%)

'''
def camera_recog():
    print("[INFO] camera sensor warming up...")
    vs = cv2.VideoCapture(0); #get input from webcam
    toggle = 0
    framecnt = 0
    if vs:
        while True:
            key = cv2.waitKey(1) & 0xFF
            _,frame = vs.read();
            if key == ord("k"):
                print("Detecting Face....")
                toggle = 1
            #u can certainly add a roi here but for the sake of a demo i'll just leave it as simple as this
            if toggle == 1:
                rects, landmarks = face_detect.detect_face(frame,85);#min face size is set to 80x80
                aligns = []
                positions = []
                if len(rects) == 0:
                    print("No Face Detected")
                    toggle = 0
                else:
                    print("Recognizing Face...")
                    for (i, rect) in enumerate(rects):
                        aligned_face, face_pos = aligner.align(160,frame,landmarks[i])
                        if len(aligned_face) == 160 and len(aligned_face[0]) == 160:
                            aligns.append(aligned_face)
                            positions.append(face_pos)
                        else:
                            print("Align face failed") #log
                        if(len(aligns) > 0):
                            features_arr = extract_feature.get_features(aligns)
                        for (i,rect) in enumerate(rects):
                            recog_data = findPeople(features_arr,positions);
                            # cv2.rectangle(frame,(rect[0],rect[1]),(rect[0] + rect[2],rect[1]+rect[3]),(255,0,0)) #draw bounding box for the face
                            # cv2.putText(frame,recog_data[i][0]+" - "+str(recog_data[i][1])+"%",(rect[0],rect[1]),cv2.FONT_HERSHEY_SIMPLEX,1,(255,255,255),1,cv2.LINE_AA)
                            if len(recog_data) > 1:
                                print("More than one person")
                                framecnt = 0
                                toggle = 0
                                text_alert("More than one person")
                                return "More than one person"
                            elif recog_data[0][1] >= 90:
                                print(recog_data[0][i])
                                framecnt = 0
                                toggle = 0
                                text_alert(recog_data[0][i])
                                return recog_data[0][i]
                            else:
                                framecnt=framecnt+1
                                print(framecnt)
                        if framecnt == 25:
                            toggle = 0
                            print("Unknown face!")
                            text_alert("Unknown")
                            return("Unknown")
            cv2.imshow("Frame",frame)
            if key == ord("q"):
                break
    else:
        print("Camera doesn't work")
'''
facerec_128D.txt Data Structure:
{
"Person ID": {
    "Center": [[128D vector]],
    "Left": [[128D vector]],
    "Right": [[128D Vector]]
    }
}
This function basically does a simple linear search for
^the 128D vector with the min distance to the 128D vector of the face on screen
'''
def findPeople(features_arr, positions, thres = 0.6, percent_thres = 85):
    '''
    :param features_arr: a list of 128d Features of all faces on screen
    :param positions: a list of face position types of all faces on screen
    :param thres: distance threshold
    :return: person name and percentage
    '''
    f = open('./facerec_128D.txt','r')
    data_set = json.loads(f.read());
    returnRes = [];
    for (i,features_128D) in enumerate(features_arr):
        result = "Unknown";
        smallest = sys.maxsize
        for person in data_set.keys():
            person_data = data_set[person][positions[i]];
            for data in person_data:
                distance = np.sqrt(np.sum(np.square(data-features_128D)))
                if(distance < smallest):
                    smallest = distance;
                    result = person;
        percentage =  min(100, 100 * thres / smallest)
        if percentage <= percent_thres :
            result = "Unknown"
        returnRes.append((result,percentage))
    return returnRes    

'''
Description:
User input his/her name or ID -> Images from Video Capture -> detect the face -> crop the face and align it
    -> face is then categorized in 3 types: Center, Left, Right
    -> Extract 128D vectors( face features)
    -> Append each newly extracted face 128D vector to its corresponding position type (Center, Left, Right)
    -> Press Q to stop capturing
    -> Find the center ( the mean) of those 128D vectors in each category. ( np.mean(...) )
    -> Save

'''
def create_manual_data():
    vs = cv2.VideoCapture(0); #get input from webcam

    print("Please input new user ID:")
    new_name = input(); #ez python input()
    f = open('./facerec_128D.txt','r');
    data_set = json.loads(f.read());
    person_imgs = {"Left" : [], "Right": [], "Center": []};
    person_features = {"Left" : [], "Right": [], "Center": []};
    print("Please start turning slowly. Press 'q' to save and add this new user to the dataset");
    while True:
        _, frame = vs.read();
        rects, landmarks = face_detect.detect_face(frame, 85);  # min face size is set to 80x80
        for (i, rect) in enumerate(rects):
            aligned_frame, pos = aligner.align(160,frame,landmarks[:,i]);
            if len(aligned_frame) == 160 and len(aligned_frame[0]) == 160:
                person_imgs[pos].append(aligned_frame)
                cv2.imshow("Captured face", aligned_frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break

    for pos in person_imgs: #there r some exceptions here, but I'll just leave it as this to keep it simple
        person_features[pos] = [np.mean(extract_feature.get_features(person_imgs[pos]),axis=0).tolist()]
    data_set[new_name] = person_features;
    f = open('./facerec_128D.txt', 'w');
    f.write(json.dumps(data_set))

def text_alert(whoisit):
    report = {}
    report["value1"] = whoisit
    requests.post("https://maker.ifttt.com/trigger/motion_detected/with/key/oOZxJ6O6nLgtIm6l2iwGD1j85_81X95kYsTMJM0Z-bW", data=report)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", type=str, help="Run camera recognition", default="camera")
    args = parser.parse_args(sys.argv[1:]);
    FRGraph = FaceRecGraph();
    MTCNNGraph = FaceRecGraph();
    aligner = AlignCustom();
    extract_feature = FaceFeature(FRGraph)
    face_detect = MTCNNDetect(MTCNNGraph, scale_factor=2); #scale_factor, rescales image for faster detection
    main(args);
