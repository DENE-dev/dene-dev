# -*- coding: utf-8 -*-
"""DesirabilityCNN_Hero_Villain.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1ATqNagee3oNTigiCfvCMU-aOeVoChTym
"""

# Import Libraries
import torch
import torch.nn.functional as F
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms, models
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
import os
from torch import load

def run(imagedir):
    
    ## Transform images as training data was transformed  
    images_transform = transforms.Compose([transforms.Resize((224,224)),
                                            transforms.ToTensor(),
                                            transforms.Normalize(
                                                mean=[0.485, 0.456, 0.406],
                                                std=[0.229, 0.224, 0.224]
                                            )])
    
    ## Customize ImageFolder to get filenames
    class ImageFolderWithNames(datasets.ImageFolder):
        def __getitem__(self, index):
            original_tuple = super(ImageFolderWithNames, self).__getitem__(index)
            name = self.imgs[index][0]   ## access image filename to return 
            tuple_with_name = (original_tuple + (name,))
            return tuple_with_name

    ## Loading in images using customized ImageFolderWithNames
    image_dataset = ImageFolderWithNames(imagedir, transform = images_transform)

    ## Pass in image dataset to DataLoader
    image_loader = torch.utils.data.DataLoader(image_dataset, batch_size=32, shuffle=True)

    ## Load already-trained desirability model weights
    filter_resnet_model = models.resnet18(pretrained=True)
    for param in filter_resnet_model.parameters():
        param.requires_grad = False
    num_ftrs = filter_resnet_model.fc.in_features
    filter_resnet_model.fc = nn.Linear(num_ftrs, 2)
    filter_resnet_model.load_state_dict(load(DesirabilityResNetClassifier.pth))
    filter_resnet_model.eval()

    ## Run images through filter to filter out undesirable images from imagedir
    undesirable_images = []
    desirability_classes = ['desirable', 'undesirable']
    test_data_classes = ['heroes', 'villains']

    for i, (data, label, name) in enumerate(image_loader):
        output = filter_resnet_model(data)
        _, preds = torch.max(output.data, 1)
        preds = preds.cpu().numpy() 
        for j in range(data.size()[0]):
            if desirability_classes[preds[j]] == "undesirable":
              undesirable_images.append(os.path.basename(name[j]))
    
    return undesirable_images