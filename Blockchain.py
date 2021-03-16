# Importation des librairies : 

import hashlib
import json
from time import time
from urllib.parse import urlparse
from uuid import uuid4
import copy

import requests
from flask import Flask, jsonify, request

# Définition de la classe "Blockchain":

class Blockchain:
    def _init_(self):
        self.current_transactions = []
        self.chain = []
        self.nodes = set()

        # Create the genesis block
        self.new_block(previous_hash='1', proof=100)

    def register_node(self, address):
        """
        Add a new node to the list of nodes
        :param address: Address of node. Eg. 'http://192.168.0.5:5000'
        """

        parsed_url = urlparse(address)
        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)
        elif parsed_url.path:
            # Accepts an URL without scheme like '192.168.0.5:5000'.
            self.nodes.add(parsed_url.path)
        else:
            raise ValueError('Invalid URL')


    def valid_chain(self, chain):
        """
        Determine if a given blockchain is valid
        :param chain: A blockchain
        :return: True if valid, False if not
        """

        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n-----------\n")
            # Check that the hash of the block is correct
            last_block_hash = self.hash(last_block)
            if block['previous_hash'] != last_block_hash:
                return False

            # Check that the Proof of Work is correct
            if not self.valid_proof(last_block['proof'], block['proof'], last_block_hash):
                return False

            last_block = block
            current_index += 1

        return True

    def resolve_conflicts(self):
        """
        This is our consensus algorithm, it resolves conflicts
        by replacing our chain with the longest one in the network.
        :return: True if our chain was replaced, False if not
        """

        neighbours = self.nodes
        new_chain = None

        # We're only looking for chains longer than ours
        max_length = len(self.chain)

        # Grab and verify the chains from all the nodes in our network
        for node in neighbours:
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                # Check if the length is longer and the chain is valid
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        # Replace our chain if we discovered a new, valid chain longer than ours
        if new_chain:
            self.chain = new_chain
            return True

        return False

    def new_block(self, proof, previous_hash):
        """
        Create a new Block in the Blockchain
        :param proof: The proof given by the Proof of Work algorithm
        :param previous_hash: Hash of previous Block
        :return: New Block
        """

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }

        # Reset the current list of transactions
        self.current_transactions = []

        self.chain.append(block)
        return block

    def new_transaction(self, sender, recipient, amount, name_paint=None):
        """
        Creates a new transaction to go into the next mined Block
        :param sender: Address of the Sender
        :param recipient: Address of the Recipient
        :param amount: Amount
        :param name_paint: name of the painting transactionned 
        :return: The index of the Block that will hold this transaction
        """
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
            'name_paint': name_paint,
        })

        return self.last_block['index'] + 1

# METHODE 1 : fonctions définies pour réaliser une vente aux enchères. Possible de mettre en vente plusieurs oeuvres en parallèle. Les acheteurs font des offres (pour chaque oeuvre, offre unique par acheteur dans un premier temps) qui se matérialisent par des transactions réelles. A la fin de l'enchère, on identifie le gagnant et on effectue des transactions vers les perdants pour les rembourser. 
# Voir @app.route('/method1', methods=['GET']) pour communiquer avec Postman. 

    # Dictionnaire qui contient les noms de toutes les oeuvres qui sont vendues (keys) et y sont associés les informations concernant le sender, l'amount et le recipient pour chaque enchère. 
    def dico_id(self):
        dico={}
        L = []
        for block in self.chain :
            for transaction in block['transactions']:
                L.append(transaction['name_paint'])     
        L = set(L)
        for i in L:
            dico[i]=[]
        for block in self.chain :
            for transaction in block['transactions']:
                dico[transaction['name_paint']].append([transaction['sender'],transaction['amount'],transaction['recipient']])
        return dico

    # Fonction pour trouver le "gagnant" de chaque enchère: dictionnaire qui associe chaque nom d'oeuvre (key) à l'enchère la plus haute (values contenant le send, l'amount et le recipient)
    def gagnants_encheres(self): 
        dico = self.dico_id()
        dic_winner = {}
        for id in dico : 
            max_amount = dico[id][0][1]
            nb_transac = len(dico[id])
            dic_winner[id]=dico[id][0]
            for k in range(nb_transac):
                if dico[id][k][1]>max_amount:
                    max_amount = dico[id][k][1]
                    dic_winner[id]=dico[id][k]
        return dic_winner 
        
    #Fonction pour rembourser les perdants de l'enchère
    def renvoyer_argent_perdants(self):
        for i in self.dico_id() :
            u=self.dico_id()[i]
            u.remove(self.gagnants_encheres()[i])     # On enlève la transaction gagnante et on effectue toutes les autre transactions en échangeant l'émetteur et le recepteur
            for k in u:
                self.new_transaction(k[2],k[0],k[1],'Abitbol')

# METHODE 2 : Même principe que la méthode 1, mais les participants aux enchères peuvent faire plusieurs offres. Celui ayant l'offre cumulée la plus élevée remporte l'enchère. 
# Voir @app.route('/method2', methods=['GET']) pour communiquer avec Postman. 

# La fonction marche si on considère que chaque utilisateur participe à une enchère unique (fais des offres pour une seule oeuvre)
    def liste_envoyeur(self):
        L = []
        for block in self.chain :
            for transaction in block['transactions']:
                L.append(transaction['sender'])     
        L = set(L)
        return L
    
    def mise_totale_indiv(self):
        self_2 = copy.deepcopy(self)
        #chain_modified = list(self.chain) 
        L = self_2.liste_envoyeur()
        for i in L:
            somme = 0   #Somme de toutes les transactions pour chaque utilisateur
            for block in self_2.chain:
                for transaction in block['transactions']:
                    if transaction['sender'] == i:
                        somme += transaction['amount']
                        transaction['amount'] = somme  #Modifie la valeur amount des transactions si une surenchère est faite
        return self_2

# FIN DE LA METHODE 2 

    @property
    def last_block(self):
        return self.chain[-1]

    @staticmethod
    def hash(block):
        """
        Creates a SHA-256 hash of a Block
        :param block: Block
        """

        # We must make sure that the Dictionary is Ordered, or we'll have inconsistent hashes
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def proof_of_work(self, last_block):
        """
        Simple Proof of Work Algorithm:
         - Find a number p' such that hash(pp') contains leading 4 zeroes
         - Where p is the previous proof, and p' is the new proof
         
        :param last_block: <dict> last Block
        :return: <int>
        """

        last_proof = last_block['proof']
        last_hash = self.hash(last_block)

        proof = 0
        while self.valid_proof(last_proof, proof, last_hash) is False:
            proof += 1

        return proof

    @staticmethod
    def valid_proof(last_proof, proof, last_hash):
        """
        Validates the Proof
        :param last_proof: <int> Previous Proof
        :param proof: <int> Current Proof
        :param last_hash: <str> The hash of the Previous Block
        :return: <bool> True if correct, False if not.
        """

        guess = f'{last_proof}{proof}{last_hash}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"



# Instantiate the Node
app = Flask(_name_)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

# Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')

# Instantiate the Blockchain
blockchain1 = Blockchain()


@app.route('/mine', methods=['GET'])
def mine():
    # We run the proof of work algorithm to get the next proof...
    last_block = blockchain1.last_block
    proof = blockchain1.proof_of_work(last_block)

    # We must receive a reward for finding the proof.
    # The sender is "0" to signify that this node has mined a new coin.
    blockchain1.new_transaction(
        sender="0",
        recipient=node_identifier,
        amount=1,
        name_paint='None'
    )

    # Forge the new Block by adding it to the chain
    previous_hash = blockchain1.hash(last_block)
    block = blockchain1.new_block(proof, previous_hash)

    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response), 200


@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json(force=True)
    #print(values)

    # Check that the required fields are in the POST'ed data
    required = ['sender', 'recipient', 'amount','name_paint']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # Create a new Transaction
    index = blockchain1.new_transaction(values['sender'], values['recipient'], values['amount'],values['name_paint'])

    response = {'message': f'Transaction will be added to Block {index}'}
    return jsonify(response), 201


@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain1.chain,
        'length': len(blockchain1.chain),
    }
    return jsonify(response), 200


@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        blockchain1.register_node(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain1.nodes),
    }
    return jsonify(response), 201


@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain1.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain1.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain1.chain
        }

    return jsonify(response), 200

@app.route('/transactions/refund', methods=['POST'])
def refund_transaction():
    values = request.get_json(force=True)

    # Check that the required fields are in the POST'ed data
    required = ['sender', 'recipient', 'amount','name_paint']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # Create a new Transaction
    index = blockchain1.new_transaction(values['sender'], values['recipient'], values['amount'],values['name_paint'])

    response = {'message': f'Transaction will be added to Block {index}'}
    return jsonify(response), 201


# Route relative à la METHODE 1: Système de vente aux enchères simplifié (Une enchère possible par acheteur sur une oeuvre considérée)
@app.route('/method1', methods=['GET'])
def method_1():
    dic_winner = blockchain1.gagnants_encheres()
    blockchain1.renvoyer_argent_perdants()
    #return "On va effectuer les transactions suivantes comme remboursement" 
    return jsonify(dic_winner), 200

# Route relative à la METHODE 2: Système de vente aux enchères amélioré (Plusieurs enchères possibles par acheteur sur une oeuvre considérée)
@app.route('/method2', methods=['GET'])
def method_2():
    blockchain2 = blockchain1.mise_totale_indiv()
    dic_winner = blockchain2.gagnants_encheres()
    blockchain2.renvoyer_argent_perdants()
    #return "On va effectuer les transactions suivantes comme remboursement" 
    return jsonify(dic_winner), 200
    

if _name_ == '_main_':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    app.run(host='127.0.0.1', port=port)



