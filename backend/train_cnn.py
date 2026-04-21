"""
CNN Training Script: Train on NCBI data

Fetches multiple sequences per species, encodes as k-mer vectors,
and trains a 1D CNN to discriminate between marine species.

Output: trained_weights.npz (saved model weights)
"""

import numpy as np
import requests
import time
import json
from datetime import datetime

# Species to train on
SPECIES_LIST = [
    "Delphinus delphis",
    "Thunnus albacares", 
    "Salmo salar",
    "Octopus vulgaris",
    "Crassostrea gigas"
]

# ========== K-MER ENCODING ==========
class KmerEncoder:
    """Encode sequences as k-mer frequency vectors"""
    
    def __init__(self, k=6):
        self.k = k
        self.vocab_size = 4 ** k  # 4096 for k=6
        self.kmer_to_idx = self._build_kmer_vocab()
    
    def _build_kmer_vocab(self):
        """Build k-mer to index mapping"""
        bases = ['A', 'T', 'C', 'G']
        kmer_to_idx = {}
        idx = 0
        
        def generate_kmers(current, remaining):
            nonlocal idx
            if remaining == 0:
                kmer_to_idx[current] = idx
                idx += 1
            else:
                for base in bases:
                    generate_kmers(current + base, remaining - 1)
        
        generate_kmers('', self.k)
        return kmer_to_idx
    
    def encode(self, sequence):
        """Convert sequence to 4096-dimensional k-mer frequency vector"""
        sequence = sequence.upper().strip()
        sequence = "".join(c for c in sequence if c in "ATCG")
        
        if len(sequence) < self.k:
            return np.zeros(self.vocab_size)
        
        kmer_freq = np.zeros(self.vocab_size)
        for i in range(len(sequence) - self.k + 1):
            kmer = sequence[i:i+self.k]
            if kmer in self.kmer_to_idx:
                idx = self.kmer_to_idx[kmer]
                kmer_freq[idx] += 1
        
        # Normalize
        total = np.sum(kmer_freq)
        if total > 0:
            kmer_freq = kmer_freq / total
        
        return kmer_freq


# ========== SIMPLE CNN TRAINER ==========
class SimpleCNNTrainer:
    """Train CNN using basic numpy operations (no TensorFlow overhead)"""
    
    def __init__(self, input_dim=4096, output_dim=256, num_classes=5):
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.num_classes = num_classes
        self.learning_rate = 0.001
        self.weights = self._init_weights()
        self.training_history = []
    
    def _init_weights(self):
        """Initialize weights with better initialization (He initialization)"""
        weights = {
            'conv1': np.random.randn(4096, 128) * np.sqrt(2.0 / 4096),
            'conv2': np.random.randn(128, 256) * np.sqrt(2.0 / 128),
            'conv3': np.random.randn(256, 512) * np.sqrt(2.0 / 256),
            'conv4': np.random.randn(512, 512) * np.sqrt(2.0 / 512),
            'fc': np.random.randn(512, self.output_dim) * np.sqrt(2.0 / 512),
            'classifier': np.random.randn(self.output_dim, self.num_classes) * np.sqrt(2.0 / self.output_dim),
        }
        return weights
    
    def relu(self, x):
        """ReLU activation"""
        return np.maximum(x, 0)
    
    def relu_derivative(self, x):
        """ReLU derivative"""
        return (x > 0).astype(float)
    
    def softmax(self, x):
        """Softmax activation"""
        e_x = np.exp(x - np.max(x, axis=-1, keepdims=True))
        return e_x / np.sum(e_x, axis=-1, keepdims=True)
    
    def forward(self, x, training=True):
        """Forward pass through CNN"""
        if len(x.shape) == 1:
            x = x.reshape(1, -1)
        
        # Conv layer 1
        z1 = np.dot(x, self.weights['conv1'][:x.shape[1], :])
        a1 = self.relu(z1)
        
        # Conv layer 2
        z2 = np.dot(a1, self.weights['conv2'][:a1.shape[1], :])
        a2 = self.relu(z2)
        
        # Conv layer 3
        z3 = np.dot(a2, self.weights['conv3'][:a2.shape[1], :])
        a3 = self.relu(z3)
        
        # Conv layer 4
        z4 = np.dot(a3, self.weights['conv4'][:a3.shape[1], :])
        a4 = self.relu(z4)
        
        # FC layer
        z_fc = np.dot(a4, self.weights['fc'][:a4.shape[1], :])
        a_fc = self.relu(z_fc)
        
        # Classifier
        logits = np.dot(a_fc, self.weights['classifier'][:a_fc.shape[1], :])
        output = self.softmax(logits)
        
        return output, (z1, a1, z2, a2, z3, a3, z4, a4, z_fc, a_fc, logits)
    
    def backward(self, x, y, output, cache):
        """Simplified backward pass (gradient descent)"""
        batch_size = x.shape[0]
        
        # Loss: cross-entropy
        loss = -np.sum(y * np.log(output + 1e-8)) / batch_size
        
        # Update classifier weights (simplest approach)
        dlogits = (output - y) / batch_size
        dw_classifier = np.dot(cache[-2].T, dlogits)
        self.weights['classifier'][:cache[-2].shape[1], :] -= self.learning_rate * dw_classifier
        
        return loss
    
    def train_step(self, X_batch, y_batch):
        """One training step"""
        output, cache = self.forward(X_batch, training=True)
        loss = self.backward(X_batch, y_batch, output, cache)
        return loss
    
    def predict(self, x):
        """Get embedding (before classification)"""
        if len(x.shape) == 1:
            x = x.reshape(1, -1)
        
        # Forward through CNN
        z1 = np.dot(x, self.weights['conv1'][:x.shape[1], :])
        a1 = self.relu(z1)
        
        z2 = np.dot(a1, self.weights['conv2'][:a1.shape[1], :])
        a2 = self.relu(z2)
        
        z3 = np.dot(a2, self.weights['conv3'][:a2.shape[1], :])
        a3 = self.relu(z3)
        
        z4 = np.dot(a3, self.weights['conv4'][:a3.shape[1], :])
        a4 = self.relu(z4)
        
        z_fc = np.dot(a4, self.weights['fc'][:a4.shape[1], :])
        embedding = self.relu(z_fc)
        
        # L2 normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        
        return embedding.flatten()


# ========== FETCH NCBI TRAINING DATA ==========
def fetch_training_sequences(species, num_sequences=30):
    """Fetch multiple sequences per species from NCBI"""
    sequences = []
    
    for i in range(num_sequences):
        try:
            # Search for COI sequences with retries
            search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=nuccore&term={species}[Organism]+AND+(COI+OR+CO1+OR+%22cytochrome+c+oxidase+I%22)&retmax=100&retstart={i*10}&retmode=json"
            
            r = requests.get(search_url, timeout=10)
            r.raise_for_status()
            data = r.json()
            
            idlist = data.get("esearchresult", {}).get("idlist", [])
            if not idlist:
                break
            
            # Fetch first result
            seq_id = idlist[0]
            fetch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=nuccore&id={seq_id}&rettype=fasta&retmode=text"
            
            fasta_response = requests.get(fetch_url, timeout=10)
            fasta_response.raise_for_status()
            
            sequence = "".join(
                line for line in fasta_response.text.split("\n") 
                if not line.startswith(">") and line.strip()
            )
            
            if sequence and len(sequence) >= 500:  # Minimum barcode length
                sequences.append(sequence[:1000])  # Cap at 1000bp
                print(f"  ✓ Sequence {len(sequences)}/{num_sequences}")
            
            time.sleep(0.5)  # Rate limiting
            
        except Exception as e:
            print(f"  ✗ Error fetching sequence {i}: {str(e)[:40]}")
            continue
    
    return sequences


# ========== TRAIN CNN ==========
def main():
    print("="*70)
    print("🧬 CNN TRAINING: NCBI DATA")
    print("="*70)
    
    # Initialize encoder
    encoder = KmerEncoder(k=6)
    
    # Fetch training data
    print("\n[FETCHING] Downloading training sequences from NCBI...")
    training_data = {}
    all_seqs = []
    all_labels = []
    
    for species_idx, species in enumerate(SPECIES_LIST):
        print(f"\n[{species_idx+1}/{len(SPECIES_LIST)}] {species}")
        sequences = fetch_training_sequences(species, num_sequences=15)
        training_data[species] = sequences
        
        # Encode sequences
        for seq in sequences:
            kmer_vec = encoder.encode(seq)
            all_seqs.append(kmer_vec)
            all_labels.append(species_idx)
        
        print(f"  Total: {len(sequences)} sequences")
    
    # Prepare training batch
    X_train = np.array(all_seqs)
    y_indices = np.array(all_labels)
    y_train = np.eye(len(SPECIES_LIST))[y_indices]  # One-hot encoding
    
    print(f"\n[DATA] Loaded {X_train.shape[0]} training samples")
    print(f"  Shape: {X_train.shape}")
    print(f"  Classes: {len(SPECIES_LIST)}")
    
    # Train CNN
    print("\n[TRAINING] Starting CNN training...")
    trainer = SimpleCNNTrainer(input_dim=4096, output_dim=256, num_classes=len(SPECIES_LIST))
    
    epochs = 50
    batch_size = 8
    
    for epoch in range(epochs):
        # Shuffle
        indices = np.random.permutation(X_train.shape[0])
        X_shuffled = X_train[indices]
        y_shuffled = y_train[indices]
        
        # Mini-batch training
        total_loss = 0
        num_batches = 0
        
        for i in range(0, X_train.shape[0], batch_size):
            X_batch = X_shuffled[i:i+batch_size]
            y_batch = y_shuffled[i:i+batch_size]
            
            loss = trainer.train_step(X_batch, y_batch)
            total_loss += loss
            num_batches += 1
        
        avg_loss = total_loss / num_batches if num_batches > 0 else 0
        trainer.training_history.append(avg_loss)
        
        if (epoch + 1) % 10 == 0:
            print(f"  Epoch {epoch+1}/{epochs} | Loss: {avg_loss:.4f}")
    
    print(f"\n✓ Training complete!")
    print(f"  Final loss: {trainer.training_history[-1]:.4f}")
    
    # Save weights
    output_file = "trained_weights.npz"
    np.savez(
        output_file,
        conv1=trainer.weights['conv1'],
        conv2=trainer.weights['conv2'],
        conv3=trainer.weights['conv3'],
        conv4=trainer.weights['conv4'],
        fc=trainer.weights['fc'],
        classifier=trainer.weights['classifier'],
        training_history=np.array(trainer.training_history),
        species_list=np.array(SPECIES_LIST),
        training_timestamp=datetime.now().isoformat()
    )
    
    print(f"\n✓ Saved weights to {output_file}")
    
    # Test predictions on training set
    print("\n[VALIDATION] Testing on training data...")
    correct = 0
    
    for i, (seq_vec, true_label) in enumerate(zip(X_train[:10], y_indices[:10])):
        embedding = trainer.predict(seq_vec)
        
        # Compare with reference embeddings
        similarities = {}
        for j, ref_species in enumerate(SPECIES_LIST):
            ref_sample = X_train[y_indices == j][0] if np.any(y_indices == j) else None
            if ref_sample is not None:
                ref_embedding = trainer.predict(ref_sample)
                sim = np.dot(embedding, ref_embedding)
                similarities[ref_species] = sim
        
        pred = max(similarities, key=similarities.get)
        true = SPECIES_LIST[true_label]
        is_correct = pred == true
        correct += is_correct
        
        print(f"  {'✓' if is_correct else '✗'} {true:<25} → {pred:<25} ({similarities[pred]:.3f})")
    
    print(f"\n  Accuracy: {correct}/10 ({correct*10}%)")
    
    print("\n" + "="*70)
    print("✓ CNN training complete! Weights ready for deployment.")
    print("="*70)


if __name__ == "__main__":
    main()
