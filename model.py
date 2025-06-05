import csv
import math
import json
import random
import networkx as nx
import multiprocessing as mp
from collections import deque
from utils import chkpath, mkpath, save_frame, save_animation


FOLDER_MODELS = 'models'

def save_model(network, name=None, folder=None, indent=None):
    """Serialize network as a json file."""
    if name is None:
        name = f'_{network.NAME}'
    if folder is None:
        folder = network.NAME
    path = f'{FOLDER_MODELS}/{folder}/{name}.json'
    mkpath(path)
    with open(path, 'w+') as f:
        json.dump({ 
            'NAME': network.NAME,
            'N': network.N,
            'SECURITY': network.SECURITY,
            'MIN_PEERS': network.MIN_PEERS,
            'MAP_SIZE': network.MAP_SIZE,
            'nodes': network.nodes
        }, f, indent=indent)

def read_model(folder, name=None):
    """Parse json file to a network."""
    if name is None:
        name = f'_{folder}'
    path = f'{FOLDER_MODELS}/{folder}/{name}.json'
    if chkpath(path):
        with open(path, 'r') as f:
            d = json.load(f)
            return Network(
                d['NAME'],
                n=d['N'],
                security=d['SECURITY'],
                min_peers=d['MIN_PEERS'],
                map_size=d['MAP_SIZE'],
                nodes=d['nodes']
            )
    return None

def animate(network_name, name='animation', gif=True):
    i = 0
    while True:
        network = read_model(network_name, i)
        if network is None:
            break
        save_frame(network, i)
        i += 1
    if gif:
        print(f'{name}.gif ...', end='\r')
        save_animation(network_name, range(i), name)
        print(f'{name}.gif ok ', end='\r')


def get_distance(node1, node2):
    x = abs(node1['pos'][0] - node2['pos'][0])
    y = abs(node1['pos'][1] - node2['pos'][1])
    return round(math.sqrt(x * x + y * y), 2)

def info(n, dist):
    return {'node': n, 'dist': dist}


class Network:
    def __init__(self, name, **kwargs):
        self.NAME = name
        self.N = kwargs['n']
        self.SECURITY = kwargs['security'] # percentage
        self.MIN_PEERS = kwargs['min_peers']
        self.MAP_SIZE = kwargs['map_size']
        if 'nodes' in kwargs:
            self.nodes = kwargs['nodes']
            self.G = self.create_graph()
        else:
            self.nodes = []
            self.generate()
            self.G = self.create_graph()
            self.connect()

    def generate(self):
        safe = math.ceil(self.SECURITY/100 * self.N)
        for _ in range(self.N):
            if safe > 0:
                safe -= 1
            x = random.choice(range(self.MAP_SIZE+1))
            y = random.choice(range(self.MAP_SIZE+1))
            self.nodes.append({
                'infected': False,
                'vulnerable': not bool(safe),
                # safe works as a stop condition for the simulation
                # so invulnerable nodes must initially be unsafe
                'safe': False,
                'pos': (x, y),
                'peers': [],
            })
        # connect to x closest neighbours
        for n, node1 in enumerate(self.nodes):
            # bar = 20
            # bar_done = math.floor( (n+1)/self.N * bar )
            # bar_remaining = bar - bar_done
            # print(f'{self.NAME} [{"="*bar_done}{" "*bar_remaining}]', end='\r')
            n_peers = node1['peers']
            for m, node2 in enumerate(self.nodes):
                if m == n:
                    continue
                dist = get_distance(node1, node2)
                if len(n_peers) != self.MIN_PEERS:
                    n_peers.append(info(m, dist))
                    continue
                for p, peer in enumerate(n_peers):
                    if dist < peer['dist']:
                        n_peers[p] = info(m, dist)
                        break

    def create_graph(self):
        g = nx.Graph()
        for n, node in enumerate(self.nodes):
            for peer in node['peers']:
                edge = (n, peer['node'])
                if edge in g.edges:
                    continue
                g.add_edge(*edge)
        return g

    def connect(self):
        while True:
            subgraphs_gen = nx.connected_components(self.G)
            subgraphs = [self.G.subgraph(c) for c in subgraphs_gen]
            graph1 = subgraphs.pop(0)
            if not len(subgraphs):
                break
            best_dist = None
            best_nodes = (None, None)
            for n in graph1.nodes:
                for graph2 in subgraphs:
                    for m in graph2.nodes:
                        dist = get_distance(self.nodes[n], self.nodes[m])
                        if not best_dist or dist < best_dist:
                            best_dist = dist
                            best_nodes = (n, m)
            n, m = best_nodes
            self.nodes[n]['peers'].append(info(m, best_dist))
            self.nodes[m]['peers'].append(info(n, best_dist))
            for edge in ((n, m), (m, n)):
                self.G.add_edge(*edge)

    def simulate(self, save=False, omicron=False):
        def infect(n, queue):
            self.nodes[n]['infected'] = True
            queue.append((n, 'infect'))

        def protect(n, queue):
            self.nodes[n]['safe'] = True
            queue.append((n, 'protect'))

        def spread(q, queue):
            infected, protected = 0, 0
            n, mode = q
            peers = [m for m in self.G.neighbors(n)]
            for p in peers:
                peer = self.nodes[p]
                if peer['infected'] or peer['safe']:
                    continue
                if mode == 'infect':
                    if not peer['vulnerable'] and not omicron:
                        protect(p, queue)
                        continue
                    infect(p, queue)
                    infected += 1
                elif mode == 'protect':
                    protect(p, queue)
                    protected += 1
            return infected, protected

        queue = deque([])
        infect(0, queue)
        # iterate
        epoch = 0
        while queue:
            # print(epoch, 'I', [i[0] for i in queue if i[1] == 'infect'])
            # print(epoch, 'P', [i[0] for i in queue if i[1] == 'protect'])
            if save:
                save_model(self, epoch)
            new_queue = deque([])
            while queue:
                q = queue.popleft()
                infected, protected = spread(q, new_queue)
                last_infection_epoch = epoch if not infected else None
                last_protection_epoch = epoch if not protected else None
            queue = new_queue
            epoch += 1

        infected, safe = 0, 0
        for node in self.nodes:
            if node['infected']:
                infected += 1
            if node['safe']:
                safe += 1

        return (
            self.SECURITY, self.MIN_PEERS,
            self.N, infected, safe,
            epoch, last_infection_epoch, last_protection_epoch,
            nx.number_of_edges(self.G), round(nx.density(self.G), 6),
            round(nx.average_shortest_path_length(self.G), 6)
        )


def run(data, filename='simulation.csv'):
    i, n, s, p, c = data
    name = f'{n}_{s}_{p}'
    network = Network(name, n=n, security=s, min_peers=p, map_size=1000)
    with open(filename, 'a', newline='') as f:
        row = network.simulate(save=False)
        writer = csv.writer(f)
        writer.writerow(row)
    if i == 0:
        save_model(network)
    bar_width = 30
    bar_done = math.floor(c * bar_width)
    bar = f'[{"="*bar_done}{" "*(bar_width-bar_done)}]'
    print(f'{bar} {round(c*100,2)}% {name} {i}')
    return network

def simulate(i):
    # amount of nodes
    N = 1000
    
    # iterations
    I = i
    # invulnerable nodes percentage
    S = (20, 30, 40, 50, 60, 70, 80)
    # minimum amount of peers
    P = (2, 3, 4, 5, 6, 7, 8)
    # count combinations
    C = I * len(S) * len(P)

    with open('simulation.csv', 'w', newline='') as f:
        header = [
            'security', 'min_peers',
            'nodes', 'nodes_infected', 'nodes_safe',
            'epochs', 'epochs_infect', 'epochs_protect',
            'edges', 'density', 'avg_path_len'
        ]
        writer = csv.writer(f)
        writer.writerow(header)

    jobs = []
    c = 0
    for i in range(I):
        for s in S:
            for p in P:
                c += 1
                jobs.append((i, N, s, p, c/C))

    with mp.Pool() as p:
        p.map(run, jobs)
        print('All jobs finished!')
        return jobs

if __name__ == '__main__':
    simulate(1000)
