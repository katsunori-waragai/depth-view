"""
library to view depth npy files.
"""

import time
from pathlib import Path

import cv2
import numpy as np
import open3d as o3d
from tqdm import tqdm


def finitemax(depth: np.ndarray) -> float:
    return np.nanmax(depth[np.isfinite(depth)])


def finitemin(depth: np.ndarray) -> float:
    return np.nanmin(depth[np.isfinite(depth)])


def normalize_image(depth_raw: np.ndarray, vmax=None, vmin=None) -> np.ndarray:
    vmin = finitemin(depth_raw) if vmin is None else vmin
    vmax = finitemax(depth_raw) if vmax is None else vmax
    depth_raw = (depth_raw - vmin) / (vmax - vmin) * 255.0
    depth_raw = depth_raw.astype(np.uint8)  # depth_raw might have NaN, PosInf, NegInf.
    return depth_raw


def depth_as_colorimage(depth_raw: np.ndarray, vmin=None, vmax=None, colormap=cv2.COLORMAP_INFERNO) -> np.ndarray:
    """
    apply color mapping with vmin, vmax
    """
    depth_raw = normalize_image(depth_raw, vmax, vmin)
    return cv2.applyColorMap(depth_raw, colormap)


def depth_as_gray(depth_raw: np.ndarray, vmin=None, vmax=None) -> np.ndarray:
    """
    apply color mapping with vmin, vmax
    """
    gray = normalize_image(depth_raw, vmax, vmin)
    return cv2.merge((gray, gray, gray))


def resize_image(image: np.ndarray, rate: float) -> np.ndarray:
    H, W = image.shape[:2]
    return cv2.resize(image, (int(W * rate), int(H * rate)))


def as_matrix(chw_array: np.ndarray) -> np.ndarray:
    H_, W_ = chw_array.shape[-2:]
    return np.reshape(chw_array, (H_, W_))


def view_by_colormap(args):
    captured_dir = Path(args.captured_dir)
    leftdir = captured_dir / "left"
    rightdir = captured_dir / "right"
    zeddepthdir = captured_dir / "zed-depth"
    sec = args.sec
    vmax = args.vmax
    vmin = args.vmin

    left_images = sorted(leftdir.glob("**/*.png"))
    depth_npys = sorted(zeddepthdir.glob("**/*.npy"))

    for leftname, depth_name in tqdm(zip(left_images, depth_npys)):
        print(leftname, depth_name)
        image = cv2.imread(str(leftname))
        depth = np.load(str(depth_name))

        if args.gray:
            colored_depth = depth_as_gray(depth)
        elif args.jet:
            colored_depth = depth_as_colorimage(depth, vmax=vmax, vmin=vmin, colormap=cv2.COLORMAP_JET)
        elif args.inferno:
            colored_depth = depth_as_colorimage(depth, vmax=vmax, vmin=vmin, colormap=cv2.COLORMAP_INFERNO)
        else:
            colored_depth = depth_as_colorimage(depth, vmax=vmax, vmin=vmin, colormap=cv2.COLORMAP_JET)

        assert image.shape == colored_depth.shape
        assert image.dtype == colored_depth.dtype
        results = np.concatenate((image, colored_depth), axis=1)
        cv2.imshow("left depth", results)
        cv2.waitKey(10)
        time.sleep(sec)


def view3d(args):
    captured_dir = Path(args.captured_dir)
    leftdir = captured_dir / "left"
    rightdir = captured_dir / "right"
    zeddepthdir = captured_dir / "zed-depth"
    sec = args.sec

    left_images = sorted(leftdir.glob("**/*.png"))
    depth_npys = sorted(zeddepthdir.glob("**/*.npy"))

    vis = o3d.visualization.Visualizer()
    vis.create_window()
    for leftname, depth_name in zip(left_images, depth_npys):
        print(leftname, depth_name)
        image = cv2.imread(str(leftname))
        depth = np.load(str(depth_name))

        rgb = o3d.io.read_image(str(leftname))
        open3d_depth = o3d.geometry.Image(depth)
        rgbd_image = o3d.geometry.RGBDImage.create_from_color_and_depth(rgb, open3d_depth)
        # [LEFT_CAM_HD]
        height, width = image.shape[:2]
        fx = 532.41
        fy = 532.535
        cx = 636.025  # [pixel]
        cy = 362.4065  # [pixel]
        left_cam_intrinsic = o3d.camera.PinholeCameraIntrinsic(width=width, height=height, fx=fx, fy=fy, cx=cx, cy=cy)

        pcd = o3d.geometry.PointCloud.create_from_rgbd_image(rgbd_image, left_cam_intrinsic)
        pcd.transform([[1, 0, 0, 0], [0, -1, 0, 0], [0, 0, -1, 0], [0, 0, 0, 1]])
        vis.add_geometry(pcd)
        vis.update_geometry(pcd)
        vis.poll_events()
        vis.update_renderer()
        time.sleep(sec)

    vis.destroy_window()


def depth_viewer_main():
    """
    A tool to view depth(as npy file) and left image.
    In --disp3d case, use open3d to show 3D point cloud.
    """
    import argparse

    parser = argparse.ArgumentParser(description="depth npy file viewer")
    parser.add_argument("captured_dir", help="captured directory by capture.py")
    parser.add_argument("--sec", type=int, default=1, help="wait sec")
    parser.add_argument("--vmax", type=float, default=5000, help="max depth [mm]")
    parser.add_argument("--vmin", type=float, default=0, help="min depth [mm]")
    parser.add_argument("--disp3d", action="store_true", help="display 3D")
    group = parser.add_argument_group("colormap")
    group.add_argument("--gray", action="store_true", help="gray colormap")
    group.add_argument("--jet", action="store_true", help="jet colormap")
    group.add_argument("--inferno", action="store_true", help="inferno colormap")
    args = parser.parse_args()
    if args.disp3d:
        view3d(args)
    else:
        view_by_colormap(args)
