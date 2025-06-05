import os
import imageio
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
from colorutils import Color


def chkpath(path):
    return os.path.exists(path)
    
def mkpath(path):
    dir = os.path.dirname(path)
    if not chkpath(dir):
        os.makedirs(dir)


FOLDER_FRAMES = 'frames'

def save_plt(network, path):
    """Generate a plot and save it to an image file."""
    plt.figure(figsize=(20, 20))
    G = network.G
    pos = {n: node['pos'] for n, node in enumerate(network.nodes)}
    INFECTED = '#db3c2a'
    SMART = '#2a91db'
    UNSAFE = '#db942a'
    SAFE = '#2adb74'
    colors = []
    for n in G.nodes:
        node = network.nodes[n]
        color = None
        if node['infected']:
            color = INFECTED
        else:
            if not node['vulnerable']:
                color = SMART
            else:
                color = UNSAFE
                if node['safe']:
                    color = SAFE
        colors.append(color)
    if None in colors:
        raise Exception('Error: None in colors!')
    nx.draw_networkx(G, pos, node_size=250, node_color=colors, font_size=9)
    mkpath(path)
    plt.savefig(path)
    plt.close()

def save_frame(network, name=None, folder=None):
    """Add an image to the animation."""
    if name is None:
        name = f'_{network.NAME}'
    print(f'{name}.jpg ...', end='\r')
    if folder is None:
        folder = network.NAME
    path = f'{FOLDER_FRAMES}/{folder}/{name}.jpg'
    save_plt(network, path)
    print(f'{name}.jpg ok ')

def save_animation(network_name, frames, name='animation', folder=None):
    """Build a gif animation."""
    FRAMES_PER_IMG = 4  # to make the animation longer
    FRAMES_ON_LAST_IMG = 16  # for convenience
    if folder is None:
        folder = network_name
    dir = f'{FOLDER_FRAMES}/{folder}'
    output_path = f'{dir}/{name}.gif'
    mkpath(output_path)
    with imageio.get_writer(output_path, mode='I') as writer:
        for i, frame in enumerate(frames):
            path = f'{dir}/{frame}.jpg'
            if not chkpath(path):
                print('Invalid frame!')
                break
            is_last_frame = i == len(frames) - 1
            repeat = FRAMES_ON_LAST_IMG if is_last_frame else FRAMES_PER_IMG
            for _ in range(repeat):
                writer.append_data(imageio.imread(path))


def generate_palette(n, v_start=0.3, v_end=1.0, h=145, s=0.65):
    r = np.array(range(n))
    r = (r - min(r)) / (max(r) - min(r))  # normalized
    V = [v_start + (i * (v_end - v_start)) for i in r]
    HSV = [Color(hsv=(h, s, v)) for v in V]
    HEX = [c.hex for c in HSV]
    return HEX
