"""Send realistic demo RAG traces to the local API.

Simulates a RAG pipeline answering questions about the Transformer
architecture using chunked Wikipedia article text. Produces multi-span
traces with retrieval + LLM spans and detailed completion logprobs.

Usage:
    cd api && uv run python demo_traces.py

Requires: a running API server (make dev) and a seeded API key (uv run python seed.py).
"""

from __future__ import annotations

import asyncio
import sys

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.models import ApiKey

API_BASE = "http://localhost:8000"

# ---------------------------------------------------------------------------
# Wikipedia article: "Transformer (deep learning model)"
# Condensed from https://en.wikipedia.org/wiki/Transformer_(deep_learning_architecture)
# Split into 5 retrieval chunks that a real vector search might return.
# ---------------------------------------------------------------------------

CHUNK_1_HISTORY = (
    "The Transformer architecture was introduced in 2017 by researchers at Google Brain "
    "and Google Research in the landmark paper \"Attention Is All You Need\" authored by "
    "Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan N. "
    "Gomez, Lukasz Kaiser, and Illia Polosukhin. The paper was presented at the 31st "
    "Conference on Neural Information Processing Systems (NeurIPS 2017). Prior to the "
    "Transformer, the dominant sequence transduction models were based on recurrent neural "
    "networks (RNNs) such as LSTMs and GRUs, often augmented with attention mechanisms. "
    "These recurrent architectures processed tokens sequentially, which created a "
    "fundamental bottleneck: the hidden state had to carry all information about the "
    "sequence seen so far, making it difficult to capture long-range dependencies. "
    "Additionally, the sequential nature of recurrence prevented parallelization across "
    "training examples within a sequence, limiting computational efficiency on modern "
    "hardware accelerators like GPUs and TPUs."
)

CHUNK_2_ARCHITECTURE = (
    "The Transformer model follows an encoder-decoder structure using stacked self-attention "
    "and point-wise, fully connected layers for both the encoder and decoder. The encoder "
    "maps an input sequence of symbol representations to a sequence of continuous "
    "representations. The decoder then generates an output sequence of symbols one element "
    "at a time, consuming the previously generated symbols as additional input. The encoder "
    "consists of a stack of N=6 identical layers, each containing two sub-layers: a "
    "multi-head self-attention mechanism and a position-wise fully connected feed-forward "
    "network. A residual connection is employed around each of the two sub-layers, followed "
    "by layer normalization. The decoder similarly consists of N=6 identical layers but "
    "includes a third sub-layer that performs multi-head attention over the output of the "
    "encoder stack. The decoder self-attention sub-layer is modified with masking to prevent "
    "positions from attending to subsequent positions, ensuring the auto-regressive property "
    "that predictions for position i depend only on known outputs at positions less than i."
)

CHUNK_3_ATTENTION = (
    "The core innovation of the Transformer is the scaled dot-product attention mechanism. "
    "Given a set of queries Q, keys K, and values V, attention is computed as: "
    "Attention(Q, K, V) = softmax(QK^T / sqrt(d_k)) V, where d_k is the dimension of the "
    "keys. The scaling factor 1/sqrt(d_k) counteracts the tendency of the dot products to "
    "grow large in magnitude for high-dimensional keys, which would push the softmax into "
    "regions with extremely small gradients. Multi-head attention extends this by linearly "
    "projecting the queries, keys, and values h times with different learned projections, "
    "performing attention in parallel on each projection, and concatenating the results. "
    "This allows the model to jointly attend to information from different representation "
    "subspaces at different positions. The original model used h=8 parallel attention heads "
    "with d_k = d_v = d_model/h = 64. Multi-head attention provides the model with the "
    "ability to focus on different parts of the input simultaneously, capturing various "
    "types of relationships between tokens — syntactic, semantic, and positional."
)

CHUNK_4_POSITIONAL = (
    "Since the Transformer architecture contains no recurrence and no convolution, it has "
    "no inherent notion of token order. To inject information about the position of tokens "
    "in the sequence, the authors add positional encodings to the input embeddings at the "
    "bottom of the encoder and decoder stacks. The positional encodings have the same "
    "dimension d_model as the embeddings so they can be summed. The original paper used "
    "sinusoidal positional encodings defined as PE(pos, 2i) = sin(pos / 10000^(2i/d_model)) "
    "and PE(pos, 2i+1) = cos(pos / 10000^(2i/d_model)), where pos is the position and i is "
    "the dimension index. The authors hypothesized that sinusoidal encodings would allow the "
    "model to generalize to sequence lengths longer than those seen during training, since "
    "any fixed offset can be represented as a linear function of the positional encodings. "
    "Later work introduced learned positional embeddings (BERT), rotary position embeddings "
    "or RoPE (used in LLaMA, PaLM), and ALiBi (Attention with Linear Biases), each offering "
    "different trade-offs between extrapolation ability and computational cost."
)

CHUNK_5_IMPACT = (
    "The Transformer has had an enormous impact on natural language processing and artificial "
    "intelligence more broadly. BERT (Bidirectional Encoder Representations from Transformers), "
    "published by Google in 2018, used only the encoder portion to achieve state-of-the-art "
    "results on 11 NLP benchmarks by pre-training on masked language modeling and next-sentence "
    "prediction. The GPT (Generative Pre-trained Transformer) family from OpenAI uses only the "
    "decoder portion, trained autoregressively on large text corpora. GPT-2 (2019) demonstrated "
    "zero-shot task transfer, GPT-3 (2020) with 175 billion parameters showed few-shot learning "
    "capabilities, and GPT-4 (2023) achieved human-level performance on many professional exams. "
    "Beyond text, Transformers now power Vision Transformers (ViT) for image classification, "
    "DALL-E and Stable Diffusion for image generation, AlphaFold 2 for protein structure "
    "prediction, and multimodal models like Gemini and Claude that process text, images, and "
    "code jointly. The architecture's ability to scale with data and compute — following "
    "scaling laws identified by Kaplan et al. (2020) — has made it the foundation of the "
    "modern AI landscape."
)

# ---------------------------------------------------------------------------
# Demo traces — 3 different questions, each a full RAG pipeline
# ---------------------------------------------------------------------------


def _demo_trace_1() -> list[dict]:
    """Q: How does the attention mechanism work in Transformers?"""
    trace_id = "demo_trace_transformer_attn"
    prompt = (
        "[system]\n"
        "You are a knowledgeable AI assistant specializing in machine learning and deep "
        "learning architectures. Answer the user's question using ONLY the provided context "
        "documents. Cite specific details from the documents. If the context does not contain "
        "enough information, say so explicitly. Be precise and technical.\n"
        f"<doc title=\"History and Origins\">{CHUNK_1_HISTORY}</doc>\n"
        f"<doc title=\"Architecture Overview\">{CHUNK_2_ARCHITECTURE}</doc>\n"
        f"<doc title=\"Attention Mechanism\">{CHUNK_3_ATTENTION}</doc>\n"
        f"<doc title=\"Positional Encoding\">{CHUNK_4_POSITIONAL}</doc>\n"
        f"<doc title=\"Impact and Successors\">{CHUNK_5_IMPACT}</doc>\n\n"
        "[user]\n"
        "How does the attention mechanism work in Transformers? Explain the math behind "
        "scaled dot-product attention and why multi-head attention is used."
    )

    completion = (
        "The Transformer uses scaled dot-product attention as its core mechanism. Given "
        "queries Q, keys K, and values V, attention is computed as:\n\n"
        "Attention(Q, K, V) = softmax(QK^T / sqrt(d_k)) V\n\n"
        "where d_k is the dimension of the keys. The scaling factor 1/sqrt(d_k) is critical "
        "because without it, the dot products grow large in magnitude for high-dimensional "
        "keys, pushing the softmax function into regions with extremely small gradients, "
        "which would impede learning.\n\n"
        "Multi-head attention extends this by projecting queries, keys, and values h times "
        "with different learned linear projections, performing attention in parallel on each "
        "projection, and concatenating the results. The original Transformer used h=8 parallel "
        "attention heads with d_k = d_v = 64 (since d_model = 512). This allows the model to "
        "jointly attend to information from different representation subspaces at different "
        "positions — for example, one head might capture syntactic dependencies while another "
        "captures semantic relationships between tokens."
    )

    # Logprobs: confident on common connective words, uncertain on specific
    # technical facts drawn from the retrieval chunks
    logprobs = [
        {"token": "The", "logprob": -0.05},
        {"token": " Transformer", "logprob": -0.08},
        {"token": " uses", "logprob": -0.12},
        {"token": " scaled", "logprob": -0.25},
        {"token": " dot", "logprob": -0.18},
        {"token": "-product", "logprob": -0.10},
        {"token": " attention", "logprob": -0.06},
        {"token": " as", "logprob": -0.04},
        {"token": " its", "logprob": -0.08},
        {"token": " core", "logprob": -0.15},
        {"token": " mechanism", "logprob": -0.10},
        {"token": ".", "logprob": -0.03},
        {"token": " Given", "logprob": -0.20},
        {"token": " queries", "logprob": -0.35},
        {"token": " Q", "logprob": -0.12},
        {"token": ",", "logprob": -0.03},
        {"token": " keys", "logprob": -0.15},
        {"token": " K", "logprob": -0.10},
        {"token": ",", "logprob": -0.02},
        {"token": " and", "logprob": -0.03},
        {"token": " values", "logprob": -0.12},
        {"token": " V", "logprob": -0.08},
        {"token": ",", "logprob": -0.02},
        {"token": " attention", "logprob": -0.05},
        {"token": " is", "logprob": -0.03},
        {"token": " computed", "logprob": -0.10},
        {"token": " as", "logprob": -0.04},
        {"token": ":", "logprob": -0.03},
        {"token": "\n\n", "logprob": -0.08},
        {"token": "Attention", "logprob": -0.15},
        {"token": "(Q", "logprob": -0.20},
        {"token": ",", "logprob": -0.03},
        {"token": " K", "logprob": -0.05},
        {"token": ",", "logprob": -0.02},
        {"token": " V", "logprob": -0.05},
        {"token": ")", "logprob": -0.03},
        {"token": " =", "logprob": -0.05},
        {"token": " softmax", "logprob": -0.12},
        {"token": "(QK", "logprob": -0.30},
        {"token": "^T", "logprob": -0.15},
        {"token": " /", "logprob": -0.08},
        {"token": " sqrt", "logprob": -0.10},
        {"token": "(d", "logprob": -0.18},
        {"token": "_k", "logprob": -0.12},
        {"token": "))", "logprob": -0.06},
        {"token": " V", "logprob": -0.08},
        {"token": "\n\n", "logprob": -0.05},
        {"token": "where", "logprob": -0.10},
        {"token": " d", "logprob": -0.08},
        {"token": "_k", "logprob": -0.06},
        {"token": " is", "logprob": -0.03},
        {"token": " the", "logprob": -0.02},
        {"token": " dimension", "logprob": -0.08},
        {"token": " of", "logprob": -0.03},
        {"token": " the", "logprob": -0.02},
        {"token": " keys", "logprob": -0.12},
        {"token": ".", "logprob": -0.02},
        {"token": " The", "logprob": -0.06},
        {"token": " scaling", "logprob": -0.15},
        {"token": " factor", "logprob": -0.08},
        {"token": " 1", "logprob": -0.20},
        {"token": "/sqrt", "logprob": -0.18},
        {"token": "(d", "logprob": -0.10},
        {"token": "_k", "logprob": -0.08},
        {"token": ")", "logprob": -0.03},
        {"token": " is", "logprob": -0.03},
        {"token": " critical", "logprob": -0.35},
        {"token": " because", "logprob": -0.08},
        {"token": " without", "logprob": -0.18},
        {"token": " it", "logprob": -0.05},
        {"token": ",", "logprob": -0.02},
        {"token": " the", "logprob": -0.02},
        {"token": " dot", "logprob": -0.12},
        {"token": " products", "logprob": -0.10},
        {"token": " grow", "logprob": -0.25},
        {"token": " large", "logprob": -0.15},
        {"token": " in", "logprob": -0.04},
        {"token": " magnitude", "logprob": -0.30},
        {"token": " for", "logprob": -0.05},
        {"token": " high", "logprob": -0.20},
        {"token": "-dimensional", "logprob": -0.15},
        {"token": " keys", "logprob": -0.08},
        {"token": ",", "logprob": -0.02},
        {"token": " pushing", "logprob": -0.35},
        {"token": " the", "logprob": -0.03},
        {"token": " softmax", "logprob": -0.12},
        {"token": " function", "logprob": -0.10},
        {"token": " into", "logprob": -0.08},
        {"token": " regions", "logprob": -0.30},
        {"token": " with", "logprob": -0.05},
        {"token": " extremely", "logprob": -0.25},
        {"token": " small", "logprob": -0.15},
        {"token": " gradients", "logprob": -0.20},
        {"token": ",", "logprob": -0.02},
        {"token": " which", "logprob": -0.05},
        {"token": " would", "logprob": -0.10},
        {"token": " impede", "logprob": -0.80},
        {"token": " learning", "logprob": -0.12},
        {"token": ".", "logprob": -0.02},
        {"token": "\n\n", "logprob": -0.06},
        {"token": "Multi", "logprob": -0.15},
        {"token": "-head", "logprob": -0.08},
        {"token": " attention", "logprob": -0.05},
        {"token": " extends", "logprob": -0.18},
        {"token": " this", "logprob": -0.06},
        {"token": " by", "logprob": -0.05},
        {"token": " projecting", "logprob": -0.25},
        {"token": " queries", "logprob": -0.15},
        {"token": ",", "logprob": -0.02},
        {"token": " keys", "logprob": -0.08},
        {"token": ",", "logprob": -0.02},
        {"token": " and", "logprob": -0.03},
        {"token": " values", "logprob": -0.10},
        {"token": " h", "logprob": -0.20},
        {"token": " times", "logprob": -0.12},
        {"token": " with", "logprob": -0.04},
        {"token": " different", "logprob": -0.10},
        {"token": " learned", "logprob": -0.18},
        {"token": " linear", "logprob": -0.22},
        {"token": " projections", "logprob": -0.15},
        {"token": ",", "logprob": -0.02},
        {"token": " performing", "logprob": -0.12},
        {"token": " attention", "logprob": -0.05},
        {"token": " in", "logprob": -0.03},
        {"token": " parallel", "logprob": -0.10},
        {"token": " on", "logprob": -0.04},
        {"token": " each", "logprob": -0.06},
        {"token": " projection", "logprob": -0.12},
        {"token": ",", "logprob": -0.02},
        {"token": " and", "logprob": -0.03},
        {"token": " concatenating", "logprob": -0.35},
        {"token": " the", "logprob": -0.03},
        {"token": " results", "logprob": -0.08},
        {"token": ".", "logprob": -0.02},
        {"token": " The", "logprob": -0.05},
        {"token": " original", "logprob": -0.15},
        {"token": " Transformer", "logprob": -0.08},
        {"token": " used", "logprob": -0.10},
        {"token": " h", "logprob": -0.12},
        {"token": "=8", "logprob": -0.45},
        {"token": " parallel", "logprob": -0.10},
        {"token": " attention", "logprob": -0.05},
        {"token": " heads", "logprob": -0.08},
        {"token": " with", "logprob": -0.04},
        {"token": " d", "logprob": -0.10},
        {"token": "_k", "logprob": -0.08},
        {"token": " =", "logprob": -0.05},
        {"token": " d", "logprob": -0.10},
        {"token": "_v", "logprob": -0.15},
        {"token": " =", "logprob": -0.05},
        {"token": " 64", "logprob": -0.55},
        {"token": " (since", "logprob": -0.30},
        {"token": " d", "logprob": -0.10},
        {"token": "_model", "logprob": -0.12},
        {"token": " =", "logprob": -0.05},
        {"token": " 512", "logprob": -0.65},
        {"token": ").", "logprob": -0.05},
        {"token": " This", "logprob": -0.06},
        {"token": " allows", "logprob": -0.10},
        {"token": " the", "logprob": -0.02},
        {"token": " model", "logprob": -0.05},
        {"token": " to", "logprob": -0.03},
        {"token": " jointly", "logprob": -0.25},
        {"token": " attend", "logprob": -0.18},
        {"token": " to", "logprob": -0.03},
        {"token": " information", "logprob": -0.08},
        {"token": " from", "logprob": -0.04},
        {"token": " different", "logprob": -0.08},
        {"token": " representation", "logprob": -0.20},
        {"token": " subspaces", "logprob": -0.40},
        {"token": " at", "logprob": -0.04},
        {"token": " different", "logprob": -0.06},
        {"token": " positions", "logprob": -0.10},
        {"token": " —", "logprob": -0.15},
        {"token": " for", "logprob": -0.06},
        {"token": " example", "logprob": -0.10},
        {"token": ",", "logprob": -0.03},
        {"token": " one", "logprob": -0.08},
        {"token": " head", "logprob": -0.12},
        {"token": " might", "logprob": -0.15},
        {"token": " capture", "logprob": -0.20},
        {"token": " syntactic", "logprob": -0.45},
        {"token": " dependencies", "logprob": -0.30},
        {"token": " while", "logprob": -0.08},
        {"token": " another", "logprob": -0.10},
        {"token": " captures", "logprob": -0.18},
        {"token": " semantic", "logprob": -0.35},
        {"token": " relationships", "logprob": -0.20},
        {"token": " between", "logprob": -0.08},
        {"token": " tokens", "logprob": -0.10},
        {"token": ".", "logprob": -0.02},
    ]

    retriever_span = {
        "trace_id": trace_id,
        "span_id": f"{trace_id}_retriever",
        "span_type": "retrieval",
        "function_name": "retriever.vector_search",
        "module": "rag_pipeline.retriever",
        "start_time": "2026-03-04T10:30:00.000+00:00",
        "end_time": "2026-03-04T10:30:00.120+00:00",
        "duration_ms": 120.0,
        "status": "ok",
        "inputs": {"query": "How does attention mechanism work in Transformers?", "top_k": 5},
        "output": {"num_results": 5, "source": "wikipedia_ml_corpus"},
        "environment": "demo",
        "tags": {"pipeline": "rag_v2", "corpus": "wikipedia"},
    }

    llm_span = {
        "trace_id": trace_id,
        "span_id": f"{trace_id}_llm",
        "parent_span_id": None,
        "span_type": "llm",
        "function_name": "llm.generate_answer",
        "module": "rag_pipeline.generator",
        "start_time": "2026-03-04T10:30:00.125+00:00",
        "end_time": "2026-03-04T10:30:02.850+00:00",
        "duration_ms": 2725.0,
        "status": "ok",
        "model": "gpt-4o-2024-11-20",
        "prompt_text": prompt,
        "completion_text": completion,
        "completion_logprobs": logprobs,
        "prompt_tokens": 1842,
        "completion_tokens": 186,
        "environment": "demo",
        "tags": {"pipeline": "rag_v2", "temperature": "0.2"},
    }

    return [retriever_span, llm_span]


def _demo_trace_2() -> list[dict]:
    """Q: Who created the Transformer and what problem did it solve?"""
    trace_id = "demo_trace_transformer_origin"
    prompt = (
        "[system]\n"
        "You are a knowledgeable AI assistant specializing in machine learning and deep "
        "learning architectures. Answer the user's question using ONLY the provided context "
        "documents. Cite specific details from the documents. If the context does not contain "
        "enough information, say so explicitly. Be precise and technical.\n"
        f"<doc title=\"History and Origins\">{CHUNK_1_HISTORY}</doc>\n"
        f"<doc title=\"Architecture Overview\">{CHUNK_2_ARCHITECTURE}</doc>\n"
        f"<doc title=\"Attention Mechanism\">{CHUNK_3_ATTENTION}</doc>\n"
        f"<doc title=\"Positional Encoding\">{CHUNK_4_POSITIONAL}</doc>\n"
        f"<doc title=\"Impact and Successors\">{CHUNK_5_IMPACT}</doc>\n\n"
        "[user]\n"
        "Who created the Transformer architecture and what problem were they trying to solve?"
    )

    completion = (
        "The Transformer was created by researchers at Google Brain and Google Research. The "
        "eight authors of the 2017 paper \"Attention Is All You Need\" were Ashish Vaswani, "
        "Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan N. Gomez, Lukasz "
        "Kaiser, and Illia Polosukhin. The paper was presented at NeurIPS 2017.\n\n"
        "The key problem they were solving was the fundamental bottleneck of recurrent neural "
        "networks (RNNs) like LSTMs and GRUs. These models processed tokens sequentially, "
        "meaning the hidden state had to carry all information about the sequence seen so far, "
        "making it difficult to capture long-range dependencies. Additionally, the sequential "
        "nature of recurrence prevented parallelization within a sequence, severely limiting "
        "computational efficiency on GPUs and TPUs. The Transformer eliminated recurrence "
        "entirely, relying instead on self-attention to model dependencies regardless of "
        "distance in the sequence."
    )

    logprobs = [
        {"token": "The", "logprob": -0.04},
        {"token": " Transformer", "logprob": -0.06},
        {"token": " was", "logprob": -0.05},
        {"token": " created", "logprob": -0.10},
        {"token": " by", "logprob": -0.04},
        {"token": " researchers", "logprob": -0.12},
        {"token": " at", "logprob": -0.03},
        {"token": " Google", "logprob": -0.15},
        {"token": " Brain", "logprob": -0.25},
        {"token": " and", "logprob": -0.03},
        {"token": " Google", "logprob": -0.05},
        {"token": " Research", "logprob": -0.20},
        {"token": ".", "logprob": -0.02},
        {"token": " The", "logprob": -0.05},
        {"token": " eight", "logprob": -0.55},
        {"token": " authors", "logprob": -0.12},
        {"token": " of", "logprob": -0.03},
        {"token": " the", "logprob": -0.02},
        {"token": " 2017", "logprob": -0.18},
        {"token": " paper", "logprob": -0.06},
        {"token": " \"", "logprob": -0.08},
        {"token": "Attention", "logprob": -0.10},
        {"token": " Is", "logprob": -0.05},
        {"token": " All", "logprob": -0.04},
        {"token": " You", "logprob": -0.03},
        {"token": " Need", "logprob": -0.04},
        {"token": "\"", "logprob": -0.03},
        {"token": " were", "logprob": -0.06},
        {"token": " Ashish", "logprob": -0.75},
        {"token": " Vas", "logprob": -0.40},
        {"token": "wani", "logprob": -0.15},
        {"token": ",", "logprob": -0.02},
        {"token": " Noam", "logprob": -0.80},
        {"token": " Sha", "logprob": -0.45},
        {"token": "zeer", "logprob": -0.20},
        {"token": ",", "logprob": -0.02},
        {"token": " Niki", "logprob": -0.85},
        {"token": " Par", "logprob": -0.50},
        {"token": "mar", "logprob": -0.20},
        {"token": ",", "logprob": -0.02},
        {"token": " Jakob", "logprob": -0.90},
        {"token": " Usz", "logprob": -0.70},
        {"token": "koreit", "logprob": -0.25},
        {"token": ",", "logprob": -0.02},
        {"token": " Ll", "logprob": -1.20},
        {"token": "ion", "logprob": -0.30},
        {"token": " Jones", "logprob": -0.35},
        {"token": ",", "logprob": -0.02},
        {"token": " Aidan", "logprob": -0.95},
        {"token": " N", "logprob": -0.40},
        {"token": ".", "logprob": -0.05},
        {"token": " Gomez", "logprob": -0.50},
        {"token": ",", "logprob": -0.02},
        {"token": " Luk", "logprob": -1.10},
        {"token": "asz", "logprob": -0.30},
        {"token": " Kaiser", "logprob": -0.45},
        {"token": ",", "logprob": -0.02},
        {"token": " and", "logprob": -0.03},
        {"token": " Ill", "logprob": -0.95},
        {"token": "ia", "logprob": -0.25},
        {"token": " Polo", "logprob": -0.60},
        {"token": "sukhin", "logprob": -0.30},
        {"token": ".", "logprob": -0.02},
        {"token": " The", "logprob": -0.04},
        {"token": " paper", "logprob": -0.06},
        {"token": " was", "logprob": -0.05},
        {"token": " presented", "logprob": -0.12},
        {"token": " at", "logprob": -0.03},
        {"token": " Neur", "logprob": -0.20},
        {"token": "IPS", "logprob": -0.15},
        {"token": " 2017", "logprob": -0.18},
        {"token": ".", "logprob": -0.02},
        {"token": "\n\n", "logprob": -0.06},
        {"token": "The", "logprob": -0.05},
        {"token": " key", "logprob": -0.12},
        {"token": " problem", "logprob": -0.08},
        {"token": " they", "logprob": -0.06},
        {"token": " were", "logprob": -0.05},
        {"token": " solving", "logprob": -0.15},
        {"token": " was", "logprob": -0.05},
        {"token": " the", "logprob": -0.02},
        {"token": " fundamental", "logprob": -0.25},
        {"token": " bottleneck", "logprob": -0.35},
        {"token": " of", "logprob": -0.03},
        {"token": " recurrent", "logprob": -0.15},
        {"token": " neural", "logprob": -0.08},
        {"token": " networks", "logprob": -0.06},
        {"token": " (R", "logprob": -0.08},
        {"token": "NNs", "logprob": -0.10},
        {"token": ")", "logprob": -0.03},
        {"token": " like", "logprob": -0.08},
        {"token": " LST", "logprob": -0.12},
        {"token": "Ms", "logprob": -0.06},
        {"token": " and", "logprob": -0.03},
        {"token": " GR", "logprob": -0.15},
        {"token": "Us", "logprob": -0.08},
        {"token": ".", "logprob": -0.02},
        {"token": " These", "logprob": -0.06},
        {"token": " models", "logprob": -0.08},
        {"token": " processed", "logprob": -0.12},
        {"token": " tokens", "logprob": -0.08},
        {"token": " sequentially", "logprob": -0.20},
        {"token": ",", "logprob": -0.02},
        {"token": " meaning", "logprob": -0.12},
        {"token": " the", "logprob": -0.02},
        {"token": " hidden", "logprob": -0.18},
        {"token": " state", "logprob": -0.10},
        {"token": " had", "logprob": -0.06},
        {"token": " to", "logprob": -0.03},
        {"token": " carry", "logprob": -0.20},
        {"token": " all", "logprob": -0.06},
        {"token": " information", "logprob": -0.08},
        {"token": " about", "logprob": -0.04},
        {"token": " the", "logprob": -0.02},
        {"token": " sequence", "logprob": -0.08},
        {"token": " seen", "logprob": -0.15},
        {"token": " so", "logprob": -0.06},
        {"token": " far", "logprob": -0.05},
        {"token": ",", "logprob": -0.02},
        {"token": " making", "logprob": -0.08},
        {"token": " it", "logprob": -0.03},
        {"token": " difficult", "logprob": -0.12},
        {"token": " to", "logprob": -0.03},
        {"token": " capture", "logprob": -0.15},
        {"token": " long", "logprob": -0.10},
        {"token": "-range", "logprob": -0.08},
        {"token": " dependencies", "logprob": -0.12},
        {"token": ".", "logprob": -0.02},
        {"token": " Additionally", "logprob": -0.18},
        {"token": ",", "logprob": -0.02},
        {"token": " the", "logprob": -0.02},
        {"token": " sequential", "logprob": -0.12},
        {"token": " nature", "logprob": -0.10},
        {"token": " of", "logprob": -0.03},
        {"token": " recurrence", "logprob": -0.20},
        {"token": " prevented", "logprob": -0.25},
        {"token": " parallelization", "logprob": -0.35},
        {"token": " within", "logprob": -0.10},
        {"token": " a", "logprob": -0.02},
        {"token": " sequence", "logprob": -0.06},
        {"token": ",", "logprob": -0.02},
        {"token": " severely", "logprob": -0.40},
        {"token": " limiting", "logprob": -0.15},
        {"token": " computational", "logprob": -0.12},
        {"token": " efficiency", "logprob": -0.10},
        {"token": " on", "logprob": -0.03},
        {"token": " GPUs", "logprob": -0.18},
        {"token": " and", "logprob": -0.03},
        {"token": " TPUs", "logprob": -0.22},
        {"token": ".", "logprob": -0.02},
        {"token": " The", "logprob": -0.04},
        {"token": " Transformer", "logprob": -0.06},
        {"token": " eliminated", "logprob": -0.25},
        {"token": " recurrence", "logprob": -0.15},
        {"token": " entirely", "logprob": -0.18},
        {"token": ",", "logprob": -0.02},
        {"token": " relying", "logprob": -0.20},
        {"token": " instead", "logprob": -0.10},
        {"token": " on", "logprob": -0.03},
        {"token": " self", "logprob": -0.08},
        {"token": "-attention", "logprob": -0.06},
        {"token": " to", "logprob": -0.03},
        {"token": " model", "logprob": -0.08},
        {"token": " dependencies", "logprob": -0.10},
        {"token": " regardless", "logprob": -0.25},
        {"token": " of", "logprob": -0.03},
        {"token": " distance", "logprob": -0.15},
        {"token": " in", "logprob": -0.03},
        {"token": " the", "logprob": -0.02},
        {"token": " sequence", "logprob": -0.06},
        {"token": ".", "logprob": -0.02},
    ]

    retriever_span = {
        "trace_id": trace_id,
        "span_id": f"{trace_id}_retriever",
        "span_type": "retrieval",
        "function_name": "retriever.vector_search",
        "module": "rag_pipeline.retriever",
        "start_time": "2026-03-04T10:31:15.000+00:00",
        "end_time": "2026-03-04T10:31:15.095+00:00",
        "duration_ms": 95.0,
        "status": "ok",
        "inputs": {"query": "Who created the Transformer architecture?", "top_k": 5},
        "output": {"num_results": 5, "source": "wikipedia_ml_corpus"},
        "environment": "demo",
        "tags": {"pipeline": "rag_v2", "corpus": "wikipedia"},
    }

    llm_span = {
        "trace_id": trace_id,
        "span_id": f"{trace_id}_llm",
        "parent_span_id": None,
        "span_type": "llm",
        "function_name": "llm.generate_answer",
        "module": "rag_pipeline.generator",
        "start_time": "2026-03-04T10:31:15.100+00:00",
        "end_time": "2026-03-04T10:31:18.450+00:00",
        "duration_ms": 3350.0,
        "status": "ok",
        "model": "gpt-4o-2024-11-20",
        "prompt_text": prompt,
        "completion_text": completion,
        "completion_logprobs": logprobs,
        "prompt_tokens": 1842,
        "completion_tokens": 162,
        "environment": "demo",
        "tags": {"pipeline": "rag_v2", "temperature": "0.2"},
    }

    return [retriever_span, llm_span]


def _demo_trace_3() -> list[dict]:
    """Q: What impact has the Transformer had beyond NLP?"""
    trace_id = "demo_trace_transformer_impact"
    prompt = (
        "[system]\n"
        "You are a knowledgeable AI assistant specializing in machine learning and deep "
        "learning architectures. Answer the user's question using ONLY the provided context "
        "documents. Cite specific details from the documents. If the context does not contain "
        "enough information, say so explicitly. Be precise and technical.\n"
        f"<doc title=\"History and Origins\">{CHUNK_1_HISTORY}</doc>\n"
        f"<doc title=\"Architecture Overview\">{CHUNK_2_ARCHITECTURE}</doc>\n"
        f"<doc title=\"Attention Mechanism\">{CHUNK_3_ATTENTION}</doc>\n"
        f"<doc title=\"Positional Encoding\">{CHUNK_4_POSITIONAL}</doc>\n"
        f"<doc title=\"Impact and Successors\">{CHUNK_5_IMPACT}</doc>\n\n"
        "[user]\n"
        "What impact has the Transformer had beyond NLP? Give specific examples of non-text "
        "applications."
    )

    completion = (
        "The Transformer's impact extends well beyond natural language processing into several "
        "other domains:\n\n"
        "**Computer Vision**: Vision Transformers (ViT) apply the Transformer architecture to "
        "image classification by treating image patches as tokens, achieving competitive results "
        "with convolutional neural networks.\n\n"
        "**Image Generation**: Models like DALL-E and Stable Diffusion use Transformer-based "
        "architectures for text-to-image generation, producing high-quality images from natural "
        "language descriptions.\n\n"
        "**Protein Science**: AlphaFold 2 leverages Transformer attention mechanisms for protein "
        "structure prediction, solving a grand challenge in computational biology.\n\n"
        "**Multimodal AI**: Models like Gemini and Claude process text, images, and code jointly "
        "within a single Transformer-based architecture.\n\n"
        "A key enabler of this cross-domain success is the architecture's ability to scale "
        "predictably with data and compute, following the scaling laws identified by Kaplan "
        "et al. in 2020. This has made the Transformer the foundation of the modern AI landscape."
    )

    logprobs = [
        {"token": "The", "logprob": -0.04},
        {"token": " Transformer", "logprob": -0.06},
        {"token": "'s", "logprob": -0.08},
        {"token": " impact", "logprob": -0.10},
        {"token": " extends", "logprob": -0.12},
        {"token": " well", "logprob": -0.08},
        {"token": " beyond", "logprob": -0.06},
        {"token": " natural", "logprob": -0.05},
        {"token": " language", "logprob": -0.04},
        {"token": " processing", "logprob": -0.05},
        {"token": " into", "logprob": -0.06},
        {"token": " several", "logprob": -0.12},
        {"token": " other", "logprob": -0.05},
        {"token": " domains", "logprob": -0.10},
        {"token": ":", "logprob": -0.03},
        {"token": "\n\n", "logprob": -0.05},
        {"token": "**", "logprob": -0.10},
        {"token": "Computer", "logprob": -0.20},
        {"token": " Vision", "logprob": -0.08},
        {"token": "**:", "logprob": -0.05},
        {"token": " Vision", "logprob": -0.10},
        {"token": " Transformers", "logprob": -0.12},
        {"token": " (V", "logprob": -0.15},
        {"token": "iT", "logprob": -0.20},
        {"token": ")", "logprob": -0.03},
        {"token": " apply", "logprob": -0.15},
        {"token": " the", "logprob": -0.02},
        {"token": " Transformer", "logprob": -0.05},
        {"token": " architecture", "logprob": -0.06},
        {"token": " to", "logprob": -0.03},
        {"token": " image", "logprob": -0.08},
        {"token": " classification", "logprob": -0.12},
        {"token": " by", "logprob": -0.05},
        {"token": " treating", "logprob": -0.25},
        {"token": " image", "logprob": -0.08},
        {"token": " patches", "logprob": -0.35},
        {"token": " as", "logprob": -0.04},
        {"token": " tokens", "logprob": -0.10},
        {"token": ",", "logprob": -0.02},
        {"token": " achieving", "logprob": -0.15},
        {"token": " competitive", "logprob": -0.25},
        {"token": " results", "logprob": -0.08},
        {"token": " with", "logprob": -0.04},
        {"token": " convolutional", "logprob": -0.20},
        {"token": " neural", "logprob": -0.08},
        {"token": " networks", "logprob": -0.06},
        {"token": ".", "logprob": -0.02},
        {"token": "\n\n", "logprob": -0.05},
        {"token": "**", "logprob": -0.06},
        {"token": "Image", "logprob": -0.15},
        {"token": " Generation", "logprob": -0.10},
        {"token": "**:", "logprob": -0.04},
        {"token": " Models", "logprob": -0.10},
        {"token": " like", "logprob": -0.06},
        {"token": " DALL", "logprob": -0.18},
        {"token": "-E", "logprob": -0.08},
        {"token": " and", "logprob": -0.03},
        {"token": " Stable", "logprob": -0.15},
        {"token": " Diffusion", "logprob": -0.10},
        {"token": " use", "logprob": -0.06},
        {"token": " Transformer", "logprob": -0.05},
        {"token": "-based", "logprob": -0.08},
        {"token": " architectures", "logprob": -0.10},
        {"token": " for", "logprob": -0.03},
        {"token": " text", "logprob": -0.06},
        {"token": "-to", "logprob": -0.05},
        {"token": "-image", "logprob": -0.06},
        {"token": " generation", "logprob": -0.08},
        {"token": ",", "logprob": -0.02},
        {"token": " producing", "logprob": -0.15},
        {"token": " high", "logprob": -0.10},
        {"token": "-quality", "logprob": -0.08},
        {"token": " images", "logprob": -0.06},
        {"token": " from", "logprob": -0.03},
        {"token": " natural", "logprob": -0.06},
        {"token": " language", "logprob": -0.05},
        {"token": " descriptions", "logprob": -0.12},
        {"token": ".", "logprob": -0.02},
        {"token": "\n\n", "logprob": -0.04},
        {"token": "**", "logprob": -0.05},
        {"token": "Protein", "logprob": -0.25},
        {"token": " Science", "logprob": -0.18},
        {"token": "**:", "logprob": -0.04},
        {"token": " Alpha", "logprob": -0.12},
        {"token": "Fold", "logprob": -0.15},
        {"token": " 2", "logprob": -0.10},
        {"token": " leverages", "logprob": -0.30},
        {"token": " Transformer", "logprob": -0.06},
        {"token": " attention", "logprob": -0.08},
        {"token": " mechanisms", "logprob": -0.10},
        {"token": " for", "logprob": -0.03},
        {"token": " protein", "logprob": -0.08},
        {"token": " structure", "logprob": -0.06},
        {"token": " prediction", "logprob": -0.08},
        {"token": ",", "logprob": -0.02},
        {"token": " solving", "logprob": -0.25},
        {"token": " a", "logprob": -0.03},
        {"token": " grand", "logprob": -0.35},
        {"token": " challenge", "logprob": -0.18},
        {"token": " in", "logprob": -0.03},
        {"token": " computational", "logprob": -0.15},
        {"token": " biology", "logprob": -0.12},
        {"token": ".", "logprob": -0.02},
        {"token": "\n\n", "logprob": -0.04},
        {"token": "**", "logprob": -0.05},
        {"token": "Multi", "logprob": -0.10},
        {"token": "modal", "logprob": -0.08},
        {"token": " AI", "logprob": -0.05},
        {"token": "**:", "logprob": -0.04},
        {"token": " Models", "logprob": -0.08},
        {"token": " like", "logprob": -0.05},
        {"token": " Gemini", "logprob": -0.20},
        {"token": " and", "logprob": -0.03},
        {"token": " Claude", "logprob": -0.18},
        {"token": " process", "logprob": -0.10},
        {"token": " text", "logprob": -0.05},
        {"token": ",", "logprob": -0.02},
        {"token": " images", "logprob": -0.06},
        {"token": ",", "logprob": -0.02},
        {"token": " and", "logprob": -0.03},
        {"token": " code", "logprob": -0.08},
        {"token": " jointly", "logprob": -0.15},
        {"token": " within", "logprob": -0.10},
        {"token": " a", "logprob": -0.02},
        {"token": " single", "logprob": -0.08},
        {"token": " Transformer", "logprob": -0.05},
        {"token": "-based", "logprob": -0.08},
        {"token": " architecture", "logprob": -0.06},
        {"token": ".", "logprob": -0.02},
        {"token": "\n\n", "logprob": -0.05},
        {"token": "A", "logprob": -0.10},
        {"token": " key", "logprob": -0.08},
        {"token": " enabler", "logprob": -0.30},
        {"token": " of", "logprob": -0.03},
        {"token": " this", "logprob": -0.05},
        {"token": " cross", "logprob": -0.20},
        {"token": "-domain", "logprob": -0.12},
        {"token": " success", "logprob": -0.10},
        {"token": " is", "logprob": -0.04},
        {"token": " the", "logprob": -0.02},
        {"token": " architecture", "logprob": -0.06},
        {"token": "'s", "logprob": -0.04},
        {"token": " ability", "logprob": -0.08},
        {"token": " to", "logprob": -0.03},
        {"token": " scale", "logprob": -0.10},
        {"token": " predictably", "logprob": -0.35},
        {"token": " with", "logprob": -0.04},
        {"token": " data", "logprob": -0.06},
        {"token": " and", "logprob": -0.03},
        {"token": " compute", "logprob": -0.08},
        {"token": ",", "logprob": -0.02},
        {"token": " following", "logprob": -0.12},
        {"token": " the", "logprob": -0.02},
        {"token": " scaling", "logprob": -0.10},
        {"token": " laws", "logprob": -0.12},
        {"token": " identified", "logprob": -0.18},
        {"token": " by", "logprob": -0.04},
        {"token": " Kaplan", "logprob": -0.55},
        {"token": " et", "logprob": -0.10},
        {"token": " al", "logprob": -0.08},
        {"token": ".", "logprob": -0.03},
        {"token": " in", "logprob": -0.05},
        {"token": " 2020", "logprob": -0.30},
        {"token": ".", "logprob": -0.02},
        {"token": " This", "logprob": -0.06},
        {"token": " has", "logprob": -0.05},
        {"token": " made", "logprob": -0.08},
        {"token": " the", "logprob": -0.02},
        {"token": " Transformer", "logprob": -0.05},
        {"token": " the", "logprob": -0.04},
        {"token": " foundation", "logprob": -0.12},
        {"token": " of", "logprob": -0.03},
        {"token": " the", "logprob": -0.02},
        {"token": " modern", "logprob": -0.08},
        {"token": " AI", "logprob": -0.05},
        {"token": " landscape", "logprob": -0.15},
        {"token": ".", "logprob": -0.02},
    ]

    retriever_span = {
        "trace_id": trace_id,
        "span_id": f"{trace_id}_retriever",
        "span_type": "retrieval",
        "function_name": "retriever.vector_search",
        "module": "rag_pipeline.retriever",
        "start_time": "2026-03-04T10:32:45.000+00:00",
        "end_time": "2026-03-04T10:32:45.110+00:00",
        "duration_ms": 110.0,
        "status": "ok",
        "inputs": {"query": "Transformer impact beyond NLP non-text applications", "top_k": 5},
        "output": {"num_results": 5, "source": "wikipedia_ml_corpus"},
        "environment": "demo",
        "tags": {"pipeline": "rag_v2", "corpus": "wikipedia"},
    }

    llm_span = {
        "trace_id": trace_id,
        "span_id": f"{trace_id}_llm",
        "parent_span_id": None,
        "span_type": "llm",
        "function_name": "llm.generate_answer",
        "module": "rag_pipeline.generator",
        "start_time": "2026-03-04T10:32:45.115+00:00",
        "end_time": "2026-03-04T10:32:48.900+00:00",
        "duration_ms": 3785.0,
        "status": "ok",
        "model": "gpt-4o-2024-11-20",
        "prompt_text": prompt,
        "completion_text": completion,
        "completion_logprobs": logprobs,
        "prompt_tokens": 1842,
        "completion_tokens": 174,
        "environment": "demo",
        "tags": {"pipeline": "rag_v2", "temperature": "0.2"},
    }

    return [retriever_span, llm_span]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


async def _get_api_key(engine) -> str | None:  # type: ignore[type-arg]
    """Read the first API key from the database."""
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        result = await db.execute(select(ApiKey).limit(1))
        row = result.scalar_one_or_none()
        if not row:
            return None
        # Reconstruct raw key — we can't, but we can read the hash
        # and look for the key in seed output. Instead, just find it.
        return row.key_hash


async def main() -> None:
    """Send demo traces to the local API server."""

    # Read the API key directly from env or try to find it
    # The seed script prints the raw key; user should pass it as arg
    if len(sys.argv) > 1:
        api_key = sys.argv[1]
    else:
        # Try to read from the database and match against a known pattern
        print("Usage: uv run python demo_traces.py <API_KEY>")
        print("")
        print("  The API key was printed when you ran: uv run python seed.py")
        print("  It starts with 'tr_'")
        sys.exit(1)

    headers = {"X-Trace-Key": api_key}
    all_spans: list[dict] = []
    all_spans.extend(_demo_trace_1())
    all_spans.extend(_demo_trace_2())
    all_spans.extend(_demo_trace_3())

    async with httpx.AsyncClient(base_url=API_BASE, timeout=30.0) as client:
        # Ingest all spans
        print(f"Sending {len(all_spans)} spans across 3 traces...")
        resp = await client.post("/ingest/batch", json=all_spans, headers=headers)
        if resp.status_code != 200:
            print(f"Ingest failed: {resp.status_code} {resp.text}")
            sys.exit(1)
        data = resp.json()
        print(f"Accepted: {data['accepted']}, Failed: {data['failed']}")

        # Trigger attribution on each LLM span
        llm_span_ids = [s["span_id"] for s in all_spans if s["span_type"] == "llm"]
        for span_id in llm_span_ids:
            print(f"Computing attribution for {span_id}...")
            attr_resp = await client.get(
                f"/traces/spans/{span_id}/attribution",
                headers=headers,
            )
            if attr_resp.status_code == 200:
                segments = attr_resp.json()["segments"]
                scored = [s for s in segments if s.get("influence_score") is not None]
                print(f"  {len(segments)} segments, {len(scored)} scored:")
                for seg in sorted(scored, key=lambda s: s["influence_score"], reverse=True):
                    name = seg["segment_name"]
                    infl = seg["influence_score"]
                    util = seg.get("utilization_score", 0) or 0
                    print(f"    {name:25s}  influence={infl:.0%}  utilization={util:.0%}")
            else:
                print(f"  Attribution failed: {attr_resp.status_code}")

    print("\nDone! Open the dashboard to see the traces.")


if __name__ == "__main__":
    asyncio.run(main())
