import moviepy.editor as mpy
import os
import cPickle
import numpy as np
import matplotlib.pyplot as plt
from flowlib import flow_to_image
from PIL import Image

def read_flow(filename):
    """
    read optical flow from Middlebury .flo file
    :param filename: name of the flow file
    :return: optical flow data in matrix
    """
    f = open(filename, 'rb')
    magic = np.fromfile(f, np.float32, count=1)
    data2d = None

    if 202021.25 != magic:
        print 'Magic number incorrect. Invalid .flo file'
        raise ValueError
    else:
        w = np.fromfile(f, np.int32, count=1)[0]
        h = np.fromfile(f, np.int32, count=1)[0]
        #print "Reading %d x %d flo file" % (h, w)
        data2d = np.fromfile(f, np.float32, count=2 * w * h)
        # reshape data into 3D array (columns, rows, channels)
        data2d = np.resize(data2d, (h, w, 2))
    f.close()
    return data2d
  
def crop_center(img,cropx,cropy):
    y,x, _ = img.shape
    startx = x//2-(cropx//2)
    starty = y//2-(cropy//2)    
    return img[starty:starty+cropy,startx:startx+cropx, :]

def blow_up(kernel, size):
  kernel_h, kernel_w = kernel.shape
  img = np.zeros((size, size), dtype=np.float32)
  block_h = size / kernel_h
  block_w = size / kernel_w
  for i in range(kernel_h):
    for j in range(kernel_w):
      img[i*block_h:(i+1)*block_h, j*block_w:(j+1)*block_w] = kernel[i, j]
  return img

def merge(masks, orig_image, gen_image, shifted_mask, poss_move_mask, batch_num, gen_image_max):
  grey_cmap = plt.get_cmap("Greys")
  seis_cmap = plt.get_cmap("seismic")
  
  assert len(masks) == 26
  figures = masks[2:14] + [masks[0]] + masks[14:26] + [masks[1]] + [shifted_mask, orig_image, gen_image, poss_move_mask]
  h = 6
  w = 5
  img_size = 64
  gap = 3
  img = np.zeros((h * (img_size + gap), w * (img_size + gap), 3))
  for idx in xrange(len(figures)):
    i = idx % w
    j = idx // w
    if idx < len(masks):
      tmp = grey_cmap(figures[idx][batch_num][:, :, 0])[:, :, 0:3]
    elif idx == len(masks):
      tmp = seis_cmap(figures[idx][batch_num])[:, :, 0, 0:3]
    elif idx == len(masks) + 1:
      tmp = figures[idx][batch_num]
    elif idx == len(masks) + 2:
      tmp = figures[idx][batch_num] / gen_image_max
    #else:
    #  tmp = grey_cmap(blow_up(figures[idx][batch_num], img_size))[:, :, 0:3]
    else:
      tmp = grey_cmap(figures[idx][batch_num][:, :, 0])[:, :, 0:3]
    img[j*(img_size+gap):j*(img_size+gap)+img_size, i*(img_size+gap):i*(img_size+gap)+img_size, :] = \
        tmp * 255.0
  
  return img

def plot_gif(orig_images, gen_images, shifted_masks, mask_lists, poss_move_masks, output_dir, itr):
  assert len(orig_images) == len(gen_images)
  assert len(orig_images) == len(shifted_masks)
  assert len(orig_images) == len(mask_lists)
  assert len(orig_images) == len(poss_move_masks)
  
  batch_size = orig_images[0].shape[0]
  os.mkdir(os.path.join(output_dir, "itr_" + str(itr)))
  
  gen_image_max = np.max([np.max(x) for x in gen_images])
  shifted_masks = [x - 0.5 for x in shifted_masks]
  #cmap = plt.get_cmap('seismic')
  
  for i in range(batch_size):
    video = []
    for j in range(len(orig_images)):
      video.append(merge(mask_lists[j], orig_images[j], 
                         gen_images[j], shifted_masks[j], poss_move_masks[j], i, gen_image_max))
    clip = mpy.ImageSequenceClip(video, fps=2)
    clip.write_gif(os.path.join(output_dir, "itr_"+str(itr), "All_batch_" + str(i) + ".gif"),
                   verbose=False)
    
  with open(os.path.join(output_dir, "itr_"+str(itr), "shifted_mask.pickle"), "wb") as f:
    cPickle.dump(shifted_masks, f)

def plot_flo(image1, image2, flo, poss_move_mask1, poss_move_mask2, poss_move_maskt, output_dir, itr):
  grey_cmap = plt.get_cmap("Greys")
  batch_size = image1.shape[0]

  h = 2
  w = 3
  img_size = image1.shape[1]
  gap = 3
  
  if not os.path.exists(os.path.join(output_dir, "itr_"+str(itr))):
    os.makedirs(os.path.join(output_dir, "itr_"+str(itr)))
  
  for cnt in range(batch_size):
    img = np.zeros((h * (img_size + gap), w * (img_size + gap), 3))
    for idx in xrange(6):
      i = idx % w
      j = idx // w
      
      if idx == 0:
        tmp = image1[cnt] * 255.0
      elif idx == 1:
        tmp = image2[cnt] * 255.0
      elif idx == 2:
        tmp = flow_to_image(flo[cnt])
      elif idx == 3:
        tmp = grey_cmap(poss_move_mask1[cnt, :, :, 0])[:, :, 0:3] * 255.0
      elif idx == 4:
        tmp = grey_cmap(poss_move_mask2[cnt, :, :, 0])[:, :, 0:3] * 255.0
      else:
        tmp = grey_cmap(poss_move_maskt[cnt, :, :, 0])[:, :, 0:3] * 255.0
      
      img[j*(img_size+gap):j*(img_size+gap)+img_size, i*(img_size+gap):i*(img_size+gap)+img_size, :] = \
          tmp
    
    im = Image.fromarray(img.astype('uint8'))

    im.save(os.path.join(output_dir, "itr_"+str(itr), str(cnt) + ".jpeg"))
  #return img

def plot_eval(image, mask1, mask2, output_dir, itr):
  grey_cmap = plt.get_cmap("Greys")
  batch_size = image.shape[0]

  h = 2
  w = 2
  img_size = image.shape[1]
  gap = 3
  
  if not os.path.exists(os.path.join(output_dir, "itr_"+str(itr))):
    os.makedirs(os.path.join(output_dir, "itr_"+str(itr)))
  
  for cnt in range(batch_size):
    img = np.zeros((h * (img_size + gap), w * (img_size + gap), 3))
    for idx in xrange(3):
      i = idx % w
      j = idx // w
      
      if idx == 0:
        tmp = image[cnt] * 255.0
      elif idx == 1:
        tmp = grey_cmap(mask1[cnt, :, :, 0])[:, :, 0:3] * 255.0
      else:
        tmp = grey_cmap(mask2[cnt, :, :, 0])[:, :, 0:3] * 255.0
      
      img[j*(img_size+gap):j*(img_size+gap)+img_size, i*(img_size+gap):i*(img_size+gap)+img_size, :] = \
          tmp
    
    im = Image.fromarray(img.astype('uint8'))

    im.save(os.path.join(output_dir, "itr_"+str(itr), "eval_" + str(cnt) + ".jpeg"))
    

def plot_grad(var_loss_bg_mask, seg_loss_poss_move_mask, move_poss_move_mask, flo_grad_bg_mask, output_dir, itr):
  batch_size = var_loss_bg_mask.shape[0]
  h = 2
  w = 2
  img_size = var_loss_bg_mask.shape[1]
  gap = 3
  grey_cmap = plt.get_cmap("Greys")
  
  for cnt in range(batch_size):
    fig, ax = plt.subplots(nrows=2,ncols=3, figsize=(20,10))

    heatmap = ax[0, 0].pcolor(flo_grad_bg_mask[cnt, ::-1, :, 0], cmap=grey_cmap)
    fig.colorbar(heatmap, ax=ax[0, 0])
#     
#    heatmap = ax[0, 1].pcolor(-img_grad_poss_move_mask[cnt, ::-1, :, 0], cmap=grey_cmap)
#    fig.colorbar(heatmap, ax=ax[0, 1])
    
    heatmap = ax[1, 0].pcolor(var_loss_bg_mask[cnt, ::-1, :, 0], cmap=grey_cmap)
    fig.colorbar(heatmap, ax=ax[1, 0])
    
#     heatmap = ax[1, 1].pcolor(-img_grad_we_poss_move_mask[cnt, ::-1, :, 0], cmap=grey_cmap)
#     fig.colorbar(heatmap, ax=ax[1, 1])
    
    heatmap = ax[0, 2].pcolor(-move_poss_move_mask[cnt, ::-1, :, 0], cmap=grey_cmap)
    fig.colorbar(heatmap, ax=ax[0, 2])
    
    heatmap = ax[1, 2].pcolor(-seg_loss_poss_move_mask[cnt, ::-1, :, 0], cmap=grey_cmap)
    fig.colorbar(heatmap, ax=ax[1, 2])

    fig.savefig(os.path.join(output_dir, "itr_"+str(itr), "grad_" + str(cnt) + ".png"))
    plt.close(fig)
    
def plot_flo_edge(image1, flo, true_edge, pred_edge,
                 output_dir, itr):
  
  grey_cmap = plt.get_cmap("Greys")
  batch_size = image1.shape[0]

  h = 2
  w = 2
  img_size = image1.shape[1]
  gap = 3
  
  if not os.path.exists(os.path.join(output_dir, "itr_"+str(itr))):
    os.makedirs(os.path.join(output_dir, "itr_"+str(itr)))
  
  for cnt in range(batch_size):
    img = np.zeros((h * (img_size + gap), w * (img_size + gap), 3))
    for idx in xrange(h*w):
      i = idx % w
      j = idx // w
      
      if idx == 0:
        tmp = image1[cnt] * 255.0
      elif idx == 1:
        tmp = flow_to_image(flo[cnt])
      elif idx == 2:
        tmp = grey_cmap(true_edge[cnt, :, :, 0])[:, :, 0:3] * 255.0
      else:
        tmp = grey_cmap(pred_edge[cnt, :, :, 0])[:, :, 0:3] * 255.0
      
      img[j*(img_size+gap):j*(img_size+gap)+img_size, i*(img_size+gap):i*(img_size+gap)+img_size, :] = \
          tmp
    
    im = Image.fromarray(img.astype('uint8'))

    im.save(os.path.join(output_dir, "itr_"+str(itr), str(cnt) + ".jpeg"))
    

def plot_flo_learn(image1, true_flo, pred_flo, true_warp, pred_warp,
                 output_dir, itr):
  grey_cmap = plt.get_cmap("Greys")
  batch_size = image1.shape[0]
  
  h = 2
  w = 3
  img_size_h = image1.shape[1]
  img_size_w = image1.shape[2]
  gap = 3
  
  if not os.path.exists(os.path.join(output_dir, "itr_"+str(itr))):
    os.makedirs(os.path.join(output_dir, "itr_"+str(itr)))
  
  for cnt in range(batch_size):
    img = np.zeros((h * (img_size_h + gap), w * (img_size_w + gap), 3))
    for idx in xrange(5):
      i = idx % w
      j = idx // w
      
      if idx == 0:
        tmp = image1[cnt] * 255.0
      elif idx == 1:
        tmp = true_warp[cnt] * 255.0
      elif idx == 2:
        tmp = pred_warp[cnt] * 255.0
      elif idx == 3:
        tmp = flow_to_image(true_flo[cnt])
      else:
        tmp = flow_to_image(pred_flo[cnt])
      
      img[j*(img_size_h+gap):j*(img_size_h+gap)+img_size_h, i*(img_size_w+gap):i*(img_size_w+gap)+img_size_w, :] = \
          tmp
    
    im = Image.fromarray(img.astype('uint8'))

    im.save(os.path.join(output_dir, "itr_"+str(itr), str(cnt) + ".jpeg"))
    

def plot_flo_learn_symm(image1, image2, true_flo, pred_flo, true_warp, pred_warp, pred_flo_r, occu_mask, occu_mask_test,
                 output_dir, itr, get_im=False):
  grey_cmap = plt.get_cmap("Greys")
  batch_size = image1.shape[0]
  
  print(np.sum(occu_mask, axis=(1, 2, 3)))
  print(np.sum(occu_mask_test, axis=(1, 2, 3)))
  
  h = 3
  w = 4
  img_size_h = image1.shape[1]
  img_size_w = image1.shape[2]
  gap = 3
  
  if not os.path.exists(os.path.join(output_dir, "itr_"+str(itr))) and (not get_im):
    os.makedirs(os.path.join(output_dir, "itr_"+str(itr)))
  ims = []
  for cnt in range(batch_size):
    img = np.zeros((h * (img_size_h + gap), w * (img_size_w + gap), 3))
    for idx in xrange(12):
      i = idx % w
      j = idx // w
      
      if idx == 0:
        tmp = image1[cnt] * 255.0
      elif idx == 1:
        tmp = true_warp[cnt] * 255.0
      elif idx == 2:
        tmp = pred_warp[cnt] * 255.0
      elif idx == 3:
        tmp = grey_cmap(occu_mask[cnt, :, :, 0])[:, :, 0:3] * 255.0
      elif idx == 4:
        tmp = flow_to_image(true_flo[cnt])
      elif idx == 5:
        tmp = flow_to_image(pred_flo[cnt])
      elif idx == 6:
        tmp = flow_to_image(pred_flo_r[cnt])
      elif idx == 7:
        tmp = grey_cmap(occu_mask_test[cnt, :, :, 0])[:, :, 0:3] * 255.0
      elif idx == 8:
        tmp = image2[cnt] * 255.0
      elif idx == 9:
        tmp = np.abs(true_warp[cnt] - image1[cnt]) * occu_mask_test[cnt] * 255.0
      elif idx == 10:
        tmp = np.abs(pred_warp[cnt] - image1[cnt]) * occu_mask[cnt] * 255.0
      else:
        tmp = np.abs(true_warp[cnt] - image1[cnt]) * 255.0
      
      img[j*(img_size_h+gap):j*(img_size_h+gap)+img_size_h, i*(img_size_w+gap):i*(img_size_w+gap)+img_size_w, :] = \
          tmp
    
    im = Image.fromarray(img.astype('uint8'))
    ims.append(im)
    
    if not get_im:
      im.save(os.path.join(output_dir, "itr_"+str(itr), str(cnt) + ".jpeg"))
  
  return ims

def plot_flo_vis_grad(true_flo, pred_flo, loss2_flow2_grad, img_grad2_flow2_grad, grad_error2_flow2_grad,
                 output_dir, itr):
  grey_cmap = plt.get_cmap("Greys")
  batch_size = true_flo.shape[0]
  
  h = 2
  w = 2
  img_size_h = true_flo.shape[1]
  img_size_w = true_flo.shape[2]
  gap = 3
  
  if not os.path.exists(os.path.join(output_dir, "itr_"+str(itr))):
    os.makedirs(os.path.join(output_dir, "itr_"+str(itr)))
  
  for cnt in range(batch_size):
    img = np.zeros((h * (img_size_h + gap), w * (img_size_w + gap), 3))
    for idx in xrange(4):
      i = idx % w
      j = idx // w
      
      if idx == 0:
        tmp = flow_to_image(true_flo[cnt] - pred_flo[cnt])
      elif idx == 1:
        tmp = flow_to_image(loss2_flow2_grad[cnt])
      elif idx == 2:
        tmp = flow_to_image(img_grad2_flow2_grad[cnt])
      else:
        tmp = flow_to_image(grad_error2_flow2_grad[cnt])
      
      img[j*(img_size_h+gap):j*(img_size_h+gap)+img_size_h, i*(img_size_w+gap):i*(img_size_w+gap)+img_size_w, :] = \
          tmp
    
    im = Image.fromarray(img.astype('uint8'))

    im.save(os.path.join(output_dir, "itr_"+str(itr), str(cnt) + "_grad.jpeg"))

def plot_flo_fullres(orig_image1_fullres, orig_image2_fullres, orig_image1_warp, output_dir, itr):
  grey_cmap = plt.get_cmap("Greys")
  batch_size = orig_image1_fullres.shape[0]
  
  h = 2
  w = 2
  img_size_h = orig_image1_fullres.shape[1]
  img_size_w = orig_image1_fullres.shape[2]
  gap = 3
  
  if not os.path.exists(os.path.join(output_dir, "itr_"+str(itr))):
    os.makedirs(os.path.join(output_dir, "itr_"+str(itr)))
  
  for cnt in range(batch_size):
    img = np.zeros((h * (img_size_h + gap), w * (img_size_w + gap), 3))
    for idx in xrange(3):
      i = idx % w
      j = idx // w
      
      if idx == 0:
        tmp = orig_image1_fullres[cnt] * 255.0
      elif idx == 1:
        tmp = orig_image2_fullres[cnt] * 255.0
      else:
        tmp = orig_image1_warp[cnt] * 255.0
      
      img[j*(img_size_h+gap):j*(img_size_h+gap)+img_size_h, i*(img_size_w+gap):i*(img_size_w+gap)+img_size_w, :] = \
          tmp
    
    im = Image.fromarray(img.astype('uint8'))

    im.save(os.path.join(output_dir, "itr_"+str(itr), str(cnt) + "_fullres.jpeg"))
    
    image1 = Image.fromarray((orig_image1_fullres[cnt] * 255.0).astype('uint8'))
    image1 = image1.resize((img_size_w/4, img_size_h/4), Image.ANTIALIAS)
    image1.save(os.path.join(output_dir, "itr_"+str(itr), str(cnt) + "_resize.jpeg"))

def plot_flo_pyrimad(image1_3, image1_4, image1_5, image1_6, image2_3, image2_4, image2_5, image2_6, 
                         output_dir, itr):
  grey_cmap = plt.get_cmap("Greys")
  batch_size = image1_3.shape[0]
  
  h = 4
  w = 2
  img_size_h = image1_3.shape[1]
  img_size_w = image1_3.shape[2]
  gap = 3
  
  if not os.path.exists(os.path.join(output_dir, "itr_"+str(itr))):
    os.makedirs(os.path.join(output_dir, "itr_"+str(itr)))
  
  for cnt in range(batch_size):
    img = np.zeros((h * (img_size_h + gap), w * (img_size_w + gap), 3))
    for idx in xrange(8):
      i = idx % w
      j = idx // w
      
      if idx == 0:
        img[j*(img_size_h+gap):j*(img_size_h+gap)+img_size_h, i*(img_size_w+gap):i*(img_size_w+gap)+img_size_w, :] = \
          image1_3[cnt] * 255.0        
      elif idx == 1:
        img[j*(img_size_h+gap):j*(img_size_h+gap)+img_size_h, i*(img_size_w+gap):i*(img_size_w+gap)+img_size_w, :] = \
          image2_3[cnt] * 255.0 
      elif idx == 2:
        img[j*(img_size_h+gap):j*(img_size_h+gap)+img_size_h/2, i*(img_size_w+gap):i*(img_size_w+gap)+img_size_w/2, :] = \
          image1_4[cnt] * 255.0
      elif idx == 3:
        img[j*(img_size_h+gap):j*(img_size_h+gap)+img_size_h/2, i*(img_size_w+gap):i*(img_size_w+gap)+img_size_w/2, :] = \
          image2_4[cnt] * 255.0  
      elif idx == 4:
        img[j*(img_size_h+gap):j*(img_size_h+gap)+img_size_h/4, i*(img_size_w+gap):i*(img_size_w+gap)+img_size_w/4, :] = \
          image1_5[cnt] * 255.0
      elif idx == 5:
        img[j*(img_size_h+gap):j*(img_size_h+gap)+img_size_h/4, i*(img_size_w+gap):i*(img_size_w+gap)+img_size_w/4, :] = \
          image2_5[cnt] * 255.0
      elif idx == 6:
        img[j*(img_size_h+gap):j*(img_size_h+gap)+img_size_h/8, i*(img_size_w+gap):i*(img_size_w+gap)+img_size_w/8, :] = \
          image1_6[cnt] * 255.0
      else:
        img[j*(img_size_h+gap):j*(img_size_h+gap)+img_size_h/8, i*(img_size_w+gap):i*(img_size_w+gap)+img_size_w/8, :] = \
          image2_6[cnt] * 255.0
      
    im = Image.fromarray(img.astype('uint8'))

    im.save(os.path.join(output_dir, "itr_"+str(itr), str(cnt) + "_pyrimad.jpeg"))


def plot_flo_triple(image1, image2, image3, pred_flo, pred_warp, file_names,
                 output_dir, itr):
  flo_dir = "/home/wangyang59/Data/ILSVRC2016_256_flo"

  batch_size = image1.shape[0]
  h = 2
  w = 3
  img_size = image1.shape[1]
  gap = 3
  
  if not os.path.exists(os.path.join(output_dir, "itr_"+str(itr))):
    os.makedirs(os.path.join(output_dir, "itr_"+str(itr)))
  
  for cnt in range(batch_size):
    img = np.zeros((h * (img_size + gap), w * (img_size + gap), 3))
    file_name1, file_name2 = file_names[cnt][0].split(",")
    
    dir_suffix = os.path.join(file_name1.split("/")[-3], file_name1.split("/")[-2])
    flo1 = os.path.join(flo_dir, dir_suffix, file_name1.split("/")[-1].split(".")[0] + ".flo")
    flo2 = os.path.join(flo_dir, dir_suffix, file_name2.split("/")[-1].split(".")[0] + ".flo")
    
    for idx in xrange(6):
      i = idx % w
      j = idx // w
      
      if idx == 0:
        tmp = pred_warp[cnt] * 255.0
      elif idx == 1:
        tmp = image2[cnt] * 255.0
      elif idx == 2:
        tmp = image3[cnt] * 255.0
      elif idx == 3:
        tmp = flow_to_image(pred_flo[cnt])
      elif idx == 4:
        tmp = flow_to_image(crop_center(read_flow(flo1), 256, 256))  
      else:
        tmp = flow_to_image(crop_center(read_flow(flo2), 256, 256)) 
        
      
      img[j*(img_size+gap):j*(img_size+gap)+img_size, i*(img_size+gap):i*(img_size+gap)+img_size, :] = \
          tmp
    
    im = Image.fromarray(img.astype('uint8'))

    im.save(os.path.join(output_dir, "itr_"+str(itr), str(cnt) + ".jpeg"))
    
def plot_autoencoder(image1, image2, image1_recon, image1_recon2, image2_recon, output_dir, itr):
  batch_size = image1.shape[0]
  
  h = 3
  w = 2
  img_size_h = image1.shape[1]
  img_size_w = image1.shape[2]
  gap = 3
  
  if not os.path.exists(os.path.join(output_dir, "itr_"+str(itr))):
    os.makedirs(os.path.join(output_dir, "itr_"+str(itr)))
  
  for cnt in range(batch_size):
    img = np.zeros((h * (img_size_h + gap), w * (img_size_w + gap), 3))
    for idx in xrange(5):
      i = idx % w
      j = idx // w
      
      if idx == 0:
        tmp = image1[cnt] * 255.0
      elif idx == 1:
        tmp = image2[cnt] * 255.0
      elif idx == 2:
        tmp = image1_recon[cnt] * 255.0
      elif idx == 3:
        tmp = image2_recon[cnt] * 255.0
      else:
        tmp = image1_recon2[cnt] * 255.0
      
      img[j*(img_size_h+gap):j*(img_size_h+gap)+img_size_h, i*(img_size_w+gap):i*(img_size_w+gap)+img_size_w, :] = \
          tmp
    
    im = Image.fromarray(img.astype('uint8'))

    im.save(os.path.join(output_dir, "itr_"+str(itr), str(cnt) + "_recon.jpeg"))
    

def plot_general(images, h, w, output_dir, itr, suffix="", get_im=False):
  grey_cmap = plt.get_cmap("Greys")
  batch_size = images[0].shape[0]
  img_size_h = images[0].shape[1]
  img_size_w = images[0].shape[2]

  gap = 3
  
  if not os.path.exists(os.path.join(output_dir, "itr_"+str(itr))) and (not get_im):
    os.makedirs(os.path.join(output_dir, "itr_"+str(itr)))
  
  ims = []
  
  for cnt in range(batch_size):
    img = np.zeros((h * (img_size_h + gap), w * (img_size_w + gap), 3))
    for idx in xrange(len(images)):
      i = idx % w
      j = idx // w
      
      image = images[idx]
      
      if image.shape[3] == 1:
        tmp = grey_cmap(image[cnt, :, :, 0])[:, :, 0:3] * 255.0
      elif image.shape[3] == 2:
        tmp = flow_to_image(image[cnt])
      else:
        tmp = image[cnt] * 255.0
      
      img[j*(img_size_h+gap):j*(img_size_h+gap)+image.shape[1], i*(img_size_w+gap):i*(img_size_w+gap)+image.shape[2], :] = \
          tmp
    
    im = Image.fromarray(img.astype('uint8'))
    ims.append(im)
    if not get_im:
      im.save(os.path.join(output_dir, "itr_"+str(itr), str(cnt) + "_" + suffix + ".jpeg"))
  
  return ims
def main():
  def merge(masks, batch_num, cmap):
    assert len(masks) == 26
    masks = masks[2:14] + [masks[0]] + masks[14:26] + [masks[1]]
    h = 6
    w = 5
    img_size = 64
    gap = 3
    img = np.zeros((h * (img_size + gap), w * (img_size + gap), 3))
    for idx in xrange(len(masks)):
      i = idx % w
      j = idx // w
      img[j*(img_size+gap):j*(img_size+gap)+img_size, i*(img_size+gap):i*(img_size+gap)+img_size, :] = \
          cmap(masks[idx][batch_num][:, :, 0])[:, :, 0:3] * 255.0
    return img#.astype('uint8')

  with open("./tmp/data/my_multigpu_run_k=0_test/itr_40002/mask_lists.pickle") as f:
    mask_lists = cPickle.load(f)
  
  video = []
  cmap = plt.get_cmap('Greys')
  
  for i in range(8):
    video.append(merge(mask_lists[i], 1, cmap))
  clip = mpy.ImageSequenceClip(video, fps=1)
  clip.write_gif("./test.gif", verbose=False)
  
  
if __name__ == '__main__':
  main()
