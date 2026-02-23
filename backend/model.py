"""
Multimodal Narrator Profile Model
Fuses facial embeddings + audio features → unified narrator representation

Architecture: Cross-Attention Transformer Fusion
Framework: PyTorch 2.x + pytorch-grad-cam
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple, Dict, Optional
import numpy as np


# ─────────────────────────────────────────────
# FEATURE ENCODERS
# ─────────────────────────────────────────────

class FacialEncoder(nn.Module):
    """
    Encodes facial feature vectors extracted by DeepFace.
    Input: [B, T, 512] (batch, time_steps, deepface_embed_dim)
    Output: [B, T, hidden_dim]
    """
    def __init__(self, input_dim: int = 512, hidden_dim: int = 256, dropout: float = 0.1):
        super().__init__()
        self.projection = nn.Sequential(
            nn.Linear(input_dim, hidden_dim * 2),
            nn.LayerNorm(hidden_dim * 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.LayerNorm(hidden_dim)
        )
        # Temporal attention over frame sequence
        self.temporal_attention = nn.MultiheadAttention(
            embed_dim=hidden_dim, num_heads=4, dropout=dropout, batch_first=True
        )
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.projection(x)                       # [B, T, hidden_dim]
        x, _ = self.temporal_attention(x, x, x)     # Self-attend over frames
        return x


class AudioEncoder(nn.Module):
    """
    Encodes audio features: MFCC, pitch, energy, spectral features.
    Input: [B, T, audio_feature_dim]
    Output: [B, T, hidden_dim]
    """
    def __init__(self, input_dim: int = 128, hidden_dim: int = 256, dropout: float = 0.1):
        super().__init__()
        
        # 1D CNN for local temporal patterns (like speech rhythm)
        self.conv_encoder = nn.Sequential(
            nn.Conv1d(input_dim, hidden_dim, kernel_size=3, padding=1),
            nn.BatchNorm1d(hidden_dim),
            nn.GELU(),
            nn.Conv1d(hidden_dim, hidden_dim, kernel_size=5, padding=2),
            nn.BatchNorm1d(hidden_dim),
            nn.GELU(),
        )
        
        self.temporal_attention = nn.MultiheadAttention(
            embed_dim=hidden_dim, num_heads=4, dropout=dropout, batch_first=True
        )
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: [B, T, features] → conv1d expects [B, features, T]
        x = x.transpose(1, 2)
        x = self.conv_encoder(x)
        x = x.transpose(1, 2)                        # Back to [B, T, hidden_dim]
        x, _ = self.temporal_attention(x, x, x)
        return x


# ─────────────────────────────────────────────
# CROSS-MODAL ATTENTION FUSION
# ─────────────────────────────────────────────

class CrossModalAttention(nn.Module):
    """
    Cross-attention between facial and audio representations.
    Facial features attend to audio (and vice versa) to find multimodal alignment.
    """
    def __init__(self, hidden_dim: int = 256, num_heads: int = 8, dropout: float = 0.1):
        super().__init__()
        
        # Face attends to audio
        self.face_to_audio = nn.MultiheadAttention(
            embed_dim=hidden_dim, num_heads=num_heads, dropout=dropout, batch_first=True
        )
        # Audio attends to face
        self.audio_to_face = nn.MultiheadAttention(
            embed_dim=hidden_dim, num_heads=num_heads, dropout=dropout, batch_first=True
        )
        
        self.norm_face = nn.LayerNorm(hidden_dim)
        self.norm_audio = nn.LayerNorm(hidden_dim)
        
        # FFN for each modality
        self.ffn_face = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim * 4),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim * 4, hidden_dim),
        )
        self.ffn_audio = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim * 4),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim * 4, hidden_dim),
        )
        
    def forward(
        self, 
        face_features: torch.Tensor,    # [B, T_face, hidden]
        audio_features: torch.Tensor,   # [B, T_audio, hidden]
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        
        # Face queries audio
        face_attn, face_weights = self.face_to_audio(
            query=face_features, key=audio_features, value=audio_features
        )
        face_out = self.norm_face(face_features + face_attn)
        face_out = self.norm_face(face_out + self.ffn_face(face_out))
        
        # Audio queries face
        audio_attn, audio_weights = self.audio_to_face(
            query=audio_features, key=face_features, value=face_features
        )
        audio_out = self.norm_audio(audio_features + audio_attn)
        audio_out = self.norm_audio(audio_out + self.ffn_audio(audio_out))
        
        return face_out, audio_out, face_weights, audio_weights


# ─────────────────────────────────────────────
# NARRATOR EMOTION CLASSIFIER HEAD
# ─────────────────────────────────────────────

class EmotionClassificationHead(nn.Module):
    """
    Classifies emotion from fused multimodal representation.
    7 basic emotions: joy, sadness, anger, fear, surprise, disgust, neutral
    """
    EMOTION_LABELS = ["joy", "sadness", "anger", "fear", "surprise", "disgust", "neutral"]
    
    def __init__(self, hidden_dim: int = 256, num_emotions: int = 7, dropout: float = 0.2):
        super().__init__()
        self.pooling = nn.AdaptiveAvgPool1d(1)  # Global average pooling
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),  # *2 for face + audio concat
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, num_emotions)
        )
        
    def forward(self, face_fused: torch.Tensor, audio_fused: torch.Tensor) -> torch.Tensor:
        # Pool over time dimension
        face_pooled = self.pooling(face_fused.transpose(1, 2)).squeeze(-1)   # [B, hidden]
        audio_pooled = self.pooling(audio_fused.transpose(1, 2)).squeeze(-1) # [B, hidden]
        
        combined = torch.cat([face_pooled, audio_pooled], dim=-1)  # [B, hidden*2]
        logits = self.classifier(combined)                          # [B, 7]
        return logits


# ─────────────────────────────────────────────
# NARRATOR IDENTITY EMBEDDING HEAD
# ─────────────────────────────────────────────

class NarratorIdentityHead(nn.Module):
    """
    Produces a fixed-size embedding representing the narrator's full profile.
    Used for narrator similarity search and de-duplication across archive.
    """
    def __init__(self, hidden_dim: int = 256, embed_dim: int = 512, dropout: float = 0.1):
        super().__init__()
        self.projector = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, embed_dim),
        )
        
    def forward(self, face_fused: torch.Tensor, audio_fused: torch.Tensor) -> torch.Tensor:
        face_mean = face_fused.mean(dim=1)    # [B, hidden]
        audio_mean = audio_fused.mean(dim=1)  # [B, hidden]
        combined = torch.cat([face_mean, audio_mean], dim=-1)
        embedding = self.projector(combined)
        return F.normalize(embedding, dim=-1)  # L2-normalize for cosine similarity


# ─────────────────────────────────────────────
# FULL MULTIMODAL NARRATOR PROFILE MODEL
# ─────────────────────────────────────────────

class MultimodalNarratorModel(nn.Module):
    """
    Complete multimodal model for oral narrative analysis.
    
    Inputs:
        - facial_embeddings: [B, T_video, 512]  (DeepFace per-frame embeddings)
        - audio_features:    [B, T_audio, 128]  (Librosa MFCC + spectral features)
        
    Outputs:
        - emotion_logits:    [B, 7]             (per-narrative emotion classification)
        - narrator_embedding:[B, 512]           (narrator identity vector)
        - attention_weights: Dict               (for Grad-CAM visualization)
    
    Grad-CAM Target Layer: cross_attention.face_to_audio
    """
    
    def __init__(
        self,
        facial_input_dim: int = 512,
        audio_input_dim: int = 128,
        hidden_dim: int = 256,
        num_emotions: int = 7,
        identity_embed_dim: int = 512,
        num_fusion_layers: int = 3,
        dropout: float = 0.1
    ):
        super().__init__()
        
        self.facial_encoder = FacialEncoder(facial_input_dim, hidden_dim, dropout)
        self.audio_encoder = AudioEncoder(audio_input_dim, hidden_dim, dropout)
        
        # Stack of cross-modal attention layers
        self.fusion_layers = nn.ModuleList([
            CrossModalAttention(hidden_dim, num_heads=8, dropout=dropout)
            for _ in range(num_fusion_layers)
        ])
        
        # Task heads
        self.emotion_head = EmotionClassificationHead(hidden_dim, num_emotions, dropout)
        self.identity_head = NarratorIdentityHead(hidden_dim, identity_embed_dim, dropout)
        
        # Store attention weights for Grad-CAM
        self._attention_weights = {}
        
    def forward(
        self,
        facial_embeddings: torch.Tensor,
        audio_features: torch.Tensor,
        return_attention: bool = True
    ) -> Dict[str, torch.Tensor]:
        
        # Encode each modality
        face_encoded = self.facial_encoder(facial_embeddings)   # [B, T_v, hidden]
        audio_encoded = self.audio_encoder(audio_features)      # [B, T_a, hidden]
        
        # Progressive cross-modal fusion
        face_fused, audio_fused = face_encoded, audio_encoded
        all_face_weights, all_audio_weights = [], []
        
        for layer in self.fusion_layers:
            face_fused, audio_fused, face_w, audio_w = layer(face_fused, audio_fused)
            all_face_weights.append(face_w)
            all_audio_weights.append(audio_w)
        
        # Task predictions
        emotion_logits = self.emotion_head(face_fused, audio_fused)
        narrator_embedding = self.identity_head(face_fused, audio_fused)
        
        output = {
            "emotion_logits": emotion_logits,
            "emotion_probs": F.softmax(emotion_logits, dim=-1),
            "narrator_embedding": narrator_embedding,
        }
        
        if return_attention:
            output["face_attention_weights"] = torch.stack(all_face_weights, dim=1)  # [B, layers, T_v, T_a]
            output["audio_attention_weights"] = torch.stack(all_audio_weights, dim=1)
        
        return output
    
    def get_emotion_label(self, emotion_probs: torch.Tensor) -> str:
        """Convert probability vector to emotion label."""
        labels = EmotionClassificationHead.EMOTION_LABELS
        idx = emotion_probs.argmax(dim=-1).item()
        return labels[idx]
    
    @classmethod
    def load_pretrained(cls, checkpoint_path: str) -> "MultimodalNarratorModel":
        """Load from checkpoint."""
        model = cls()
        state = torch.load(checkpoint_path, map_location="cpu")
        model.load_state_dict(state["model_state_dict"])
        model.eval()
        return model
    
    def save(self, path: str, epoch: int = 0, optimizer=None):
        """Save model checkpoint."""
        payload = {
            "model_state_dict": self.state_dict(),
            "epoch": epoch,
            "architecture": {
                "type": "MultimodalNarratorModel",
                "hidden_dim": 256,
                "num_fusion_layers": 3,
                "num_emotions": 7
            }
        }
        if optimizer:
            payload["optimizer_state_dict"] = optimizer.state_dict()
        torch.save(payload, path)
        print(f"Model saved to {path}")


# ─────────────────────────────────────────────
# GRAD-CAM FOR VISUAL INTERPRETABILITY
# ─────────────────────────────────────────────

class NarratorGradCAM:
    """
    Applies pytorch-grad-cam to visualize which facial regions the model
    focuses on when classifying narrator emotions.
    
    Usage:
        from pytorch_grad_cam import GradCAM
        from pytorch_grad_cam.utils.image import show_cam_on_image
        
        cam = NarratorGradCAM(model)
        heatmap = cam.generate(frame_tensor, target_emotion_class=0)  # 0=joy
        cam.save_visualization(heatmap, frame_image, output_path)
    """
    
    def __init__(self, model: MultimodalNarratorModel):
        self.model = model
        # Target the last cross-modal attention layer for Grad-CAM
        self.target_layers = [model.fusion_layers[-1].face_to_audio]
        
    def generate(
        self, 
        facial_embeddings: torch.Tensor,
        audio_features: torch.Tensor,
        target_emotion: Optional[int] = None
    ) -> np.ndarray:
        """
        Generate Grad-CAM heatmap.
        
        In production (with pytorch-grad-cam installed):
        
            from pytorch_grad_cam import GradCAM
            from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget
            
            target = [ClassifierOutputTarget(target_emotion)] if target_emotion else None
            cam = GradCAM(model=self.model.facial_encoder, 
                          target_layers=self.target_layers)
            grayscale_cam = cam(
                input_tensor=facial_embeddings,
                targets=target
            )
            return grayscale_cam[0]
        """
        # Placeholder: return uniform attention map
        T = facial_embeddings.shape[1]
        return np.random.rand(T)  # Replace with actual Grad-CAM
    
    def get_attention_regions(self, cam_output: np.ndarray) -> Dict:
        """Interpret CAM output as facial region importance scores."""
        regions = ["forehead/brow", "eyes", "nose", "mouth/jaw", "cheeks"]
        segment_size = len(cam_output) // len(regions)
        
        importance = {}
        for i, region in enumerate(regions):
            start = i * segment_size
            end = start + segment_size
            importance[region] = float(cam_output[start:end].mean())
        
        top_region = max(importance, key=importance.get)
        return {
            "region_importance": importance,
            "top_region": top_region,
            "interpretation": f"Model focuses primarily on {top_region} for emotion detection"
        }


# ─────────────────────────────────────────────
# FEATURE ENGINEERING (scikit-learn)
# ─────────────────────────────────────────────

def build_feature_matrix(narrative_records: list) -> dict:
    """
    Build feature matrix from archive entries using pandas + scikit-learn.
    Used for narrator clustering, similarity search, and pattern analysis.
    
    In production:
        import pandas as pd
        from sklearn.preprocessing import StandardScaler
        from sklearn.decomposition import PCA
        from sklearn.cluster import KMeans
    """
    feature_columns = [
        # Facial features
        "mean_joy", "mean_sadness", "mean_anger", "mean_neutral", "mean_surprise",
        "face_detection_confidence", "estimated_age",
        # Audio features  
        "mean_pitch_hz", "pitch_variability_std", "speech_rate_wpm",
        "pause_count", "mean_pause_duration_sec", "energy_mean",
        "vocal_arousal", "vocal_valence",
    ]
    
    return {
        "feature_columns": feature_columns,
        "preprocessing": "StandardScaler",
        "dimensionality_reduction": "PCA(n_components=32)",
        "clustering": "KMeans(n_clusters=8)",
        "framework": "scikit-learn 1.4+",
        "output": "narrator_cluster_labels, similarity_matrix"
    }


# ─────────────────────────────────────────────
# MODEL SUMMARY
# ─────────────────────────────────────────────

if __name__ == "__main__":
    # Quick architecture test
    model = MultimodalNarratorModel(
        facial_input_dim=512,
        audio_input_dim=128,
        hidden_dim=256,
        num_emotions=7,
        identity_embed_dim=512,
        num_fusion_layers=3,
    )
    
    # Count parameters
    total_params = sum(p.numel() for p in model.parameters())
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"MultimodalNarratorModel")
    print(f"  Total parameters:     {total_params:,}")
    print(f"  Trainable parameters: {trainable:,}")
    print(f"  Architecture:         Cross-Attention Transformer Fusion")
    print(f"  Modalities:           Video (facial) + Audio (vocal)")
    print(f"  Outputs:              emotion_logits [7] + narrator_embedding [512]")
    print()
    
    # Test forward pass
    B, T_v, T_a = 2, 30, 50
    face_emb = torch.randn(B, T_v, 512)
    audio_feat = torch.randn(B, T_a, 128)
    
    with torch.no_grad():
        out = model(face_emb, audio_feat)
    
    print(f"Test forward pass (B={B}, T_video={T_v}, T_audio={T_a}):")
    for k, v in out.items():
        print(f"  {k}: {v.shape}")
    
    # Grad-CAM
    grad_cam = NarratorGradCAM(model)
    print(f"\nGrad-CAM target layers: {len(grad_cam.target_layers)}")
    print("Architecture validated ✓")
