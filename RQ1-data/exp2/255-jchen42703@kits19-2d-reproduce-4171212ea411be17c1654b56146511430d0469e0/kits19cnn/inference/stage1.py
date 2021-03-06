from pathlib import Path
from abc import abstractmethod
from os.path import join, isdir
from tqdm import tqdm
import os
import numpy as np
import inspect
import nibabel as nib
import torch

from kits19cnn.inference import remove_3D_connected_components, BasePredictor
from kits19cnn.io import get_bbox_from_mask, expand_bbox, crop_to_bbox, resize_bbox
from kits19.utils import load_json, save_json

class Stage1Predictor(BasePredictor):
    """
    Inference for a single model for every file generated by `test_loader`.
    Predictions are saved in `out_dir`.

    Predictions are done on the resized predictions.
    Post-processing
      * Foreground classes merged after prediction.
      * The ROIs to segment for Stage 2 were extracted creating a bounding box
        to circumscribe the union of the kidney plus the tumor (or just the
        kidneys) by using the (x, y, z) coordinates from the first stage
        segmentations.
      * After that, the bounding box was symmetrically expanded to reach the
        final size of 256×256 pixels.
        * Avoids interpolation process on the extracted images.

    """
    def __init__(self, out_dir, model, test_loader, scale_ratios_json_path,
                 pseudo_3D=True, pred_3D_params={"do_mirroring": True}):
        """
        Attributes
            out_dir (str): path to the output directory to store predictions
            model (torch.nn.Module): class with the `predict_3D` method for
                predicting a single patient volume.
            test_loader: Iterable instance for generating data
                (pref. torch DataLoader)
                must have the __len__ arg.
            scale_ratios_json_path (str): Path to the .json generated by
                `scripts/utility/create_scale_ratio_dict.py`
            pred_3D_params (dict): kwargs for `model.predict_3D`
            pseudo_3D (bool): whether or not to have pseudo 3D inputs
        """
        super().__init__(out_dir=out_dir, model=model, test_loader=test_loader)
        assert inspect.ismethod(model.predict_3D), \
                "model must have the method `predict_3D`"
        if pseudo_3D:
            assert inspect.ismethod(model.predict_3D_pseudo3D_2Dconv), \
                "model must have the method `predict_3D_pseudo3D_2Dconv`"
        self.pred_3D_params = pred_3D_params
        self.pseudo_3D = pseudo_3D
        self.bbox_coords = {}
        self.scale_ratios_dict = load_json(scale_ratios_json_path)

    def run_3D_predictions(self, min_size=5000):
        """
        Runs predictions on the dataset (specified in test_loader)
        """
        cases = self.test_loader.dataset.im_ids
        assert len(cases) == len(self.test_loader)
        for (test_batch, case) in tqdm(zip(self.test_loader, cases), total=len(cases)):
            test_x = torch.squeeze(test_batch[0], dim=0)
            if self.pseudo_3D:
                pred, _, act, _ = self.model.predict_3D_pseudo3D_2Dconv(test_x,
                                                                    **self.pred_3D_params)
            else:
                pred, _, act, _ = self.model.predict_3D(test_x,
                                                        **self.pred_3D_params)
            assert len(pred.shape) == 3
            assert len(act.shape) == 4
            pred = remove_3D_connected_components(pred, min_size=min_size)
            pred = self.post_process_stage1(pred)
            self.save_pred(pred, act, case)
            bbox_coord = self.create_bbox_stage1(pred, case)
            self.bbox_coords[case] = bbox_coord
        self.save_bbox_coords()

    def post_process_stage1(self, pred):
        """
        Foreground classes merged after prediction.
        """
        return (pred>0)*1

    def create_bbox_stage1(self, pred, case):
        """
        Creates the bounding box from the prediction.
        """
        bbox = get_bbox_from_mask(pred, outside_value=0)
        resized_bbox = resize_bbox(bbox, self.scale_ratios_dict[case])
        expanded_bbox = expand_bbox(bbox, bbox_lengths=[None, 256, 256])
        return expanded_bbox

    def save_bbox_coords(self):
        """
        Saves the bbox coords dictionary as a .json.
        """
        import json
        out_path = join(self.out_dir, "bbox_stage1.json")
        save_json(self.bbox_coords, out_path)
        print(f"Saved the bounding box coordinates at {out_path}.")