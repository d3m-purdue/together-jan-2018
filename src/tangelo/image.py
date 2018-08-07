#from __future__ import print_function
import json
import os
import tangelo
from PIL import ImageFilter, Image, ImageDraw
import base64
import cStringIO
import sys


@tangelo.restful
def get(mediafile=None,targetHeight=512,bbox=None,*args,**kwargs):
    # get the protocol versio

    dataset_path = os.environ.get('TRAINING_DATA_ROOT')

    # print 'dataset_path: ', dataset_path
    # print 'mediafile: ', mediafile

    media_file_path = dataset_path+'/media/'+mediafile
    print 'reading media file:',media_file_path
    sys.stdout.flush()

    #try:
    with open(media_file_path) as f:
        im = Image.open(f)

        width = im.width
        height = im.height

        # if a bbox is set, draw the bbox on the image here
        # before we resize.  Uncomment the line below to force a box render
        #bbox = [112,69,218,346]
        if bbox != None:
            bbox2 = bbox.split(",")
            bbox3 = [float(i) for i in bbox2]
            draw = ImageDraw.Draw(im)
            draw.rectangle(bbox3,outline=(255,255,255))
            del draw


        factor = float(targetHeight)/float(im.height)
        print('factor:',factor)
        newH = int(im.height*factor)
        newW = int(im.width*factor)
        im.resize((newW,newH))
        print 'new width:',newW, 'new height:',newH

        buffer = cStringIO.StringIO()
        im.save(buffer, format="JPEG")
        # img_str = base64.b64encode(buffer.getvalue())
        img_str = buffer.getvalue()

        tangelo.content_type('image/jpeg')
        return img_str
    #except:
    #    return {'status':'failure','mediafile':mediafile}
