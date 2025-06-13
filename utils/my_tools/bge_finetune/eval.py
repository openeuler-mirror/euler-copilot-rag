import faiss
import torch
import logging
import datasets
import json
import numpy as np
from tqdm import tqdm
from typing import Optional
from dataclasses import dataclass, field
from transformers import HfArgumentParser
from FlagEmbedding import FlagModel

logger = logging.getLogger(__name__)


@dataclass
class Args:
    encoder: str = field(
        default="BAAI/bge-base-en-v1.5",
        metadata={'help': 'The encoder name or path.'}
    )
    fp16: bool = field(
        default=False,
        metadata={'help': 'Use fp16 in inference?'}
    )
    add_instruction: bool = field(
        default=False,
        metadata={'help': 'Add query-side instruction?'}
    )
    test_data: str = field(
        default=False,
        metadata={'help': 'test_data path'}
    )
    max_query_length: int = field(
        default=32,
        metadata={'help': 'Max query length.'}
    )
    max_passage_length: int = field(
        default=128,
        metadata={'help': 'Max passage length.'}
    )
    batch_size: int = field(
        default=256,
        metadata={'help': 'Inference batch size.'}
    )
    index_factory: str = field(
        default="Flat",
        metadata={'help': 'Faiss index factory.'}
    )
    k: int = field(
        default=100,
        metadata={'help': 'How many neighbors to retrieve?'}
    )

    save_embedding: bool = field(
        default=False,
        metadata={'help': 'Save embeddings in memmap at save_dir?'}
    )
    load_embedding: bool = field(
        default=False,
        metadata={'help': 'Load embeddings from save_dir?'}
    )
    save_path: str = field(
        default="embeddings.memmap",
        metadata={'help': 'Path to save embeddings.'}
    )

def index(model: FlagModel, corpus: datasets.Dataset, batch_size: int = 256, max_length: int=512, index_factory: str = "Flat", save_path: str = None, save_embedding: bool = False, load_embedding: bool = False):
    if load_embedding:
        test = model.encode("test")
        dtype = test.dtype
        dim = len(test)

        corpus_embeddings = np.memmap(
            save_path,
            mode="r",
            dtype=dtype
        ).reshape(-1, dim)
    
    else:
        corpus_embeddings = model.encode_corpus(corpus["content"], batch_size=batch_size, max_length=max_length)
        dim = corpus_embeddings.shape[-1]
        
        if save_embedding:
            logger.info(f"saving embeddings at {save_path}...")
            memmap = np.memmap(
                save_path,
                shape=corpus_embeddings.shape,
                mode="w+",
                dtype=corpus_embeddings.dtype
            )

            length = corpus_embeddings.shape[0]
            # add in batch
            save_batch_size = 10000
            if length > save_batch_size:
                for i in tqdm(range(0, length, save_batch_size), leave=False, desc="Saving Embeddings"):
                    j = min(i + save_batch_size, length)
                    memmap[i: j] = corpus_embeddings[i: j]
            else:
                memmap[:] = corpus_embeddings
    
    # create faiss index
    faiss_index = faiss.index_factory(dim, index_factory, faiss.METRIC_INNER_PRODUCT)

    # if model.device == torch.device("cuda"):
    if False:
        co = faiss.GpuMultipleClonerOptions()
        co.useFloat16 = True
        # faiss_index = faiss.index_cpu_to_gpu(faiss.StandardGpuResources(), 0, faiss_index, co)
        faiss_index = faiss.index_cpu_to_all_gpus(faiss_index, co)

    # NOTE: faiss only accepts float32
    logger.info("Adding embeddings...")
    corpus_embeddings = corpus_embeddings.astype(np.float32)
    faiss_index.train(corpus_embeddings)
    faiss_index.add(corpus_embeddings)
    return faiss_index


def search(model: FlagModel, queries: datasets, faiss_index: faiss.Index, k:int = 100, batch_size: int = 256, max_length: int=512):
    query_embeddings = model.encode_queries(queries["query"], batch_size=batch_size, max_length=max_length)
    query_size = len(query_embeddings)
    
    all_scores = []
    all_indices = []
    
    for i in tqdm(range(0, query_size, batch_size), desc="Searching"):
        j = min(i + batch_size, query_size)
        query_embedding = query_embeddings[i: j]
        score, indice = faiss_index.search(query_embedding.astype(np.float32), k=k)
        all_scores.append(score)
        all_indices.append(indice)
    
    all_scores = np.concatenate(all_scores, axis=0)
    all_indices = np.concatenate(all_indices, axis=0)
    return all_scores, all_indices


import numpy as np


def evaluate(preds, labels, cutoffs=[1, 5, 10, 30]):
    metrics = {}

    # MRR
    mrrs = np.zeros(len(cutoffs))
    for pred, label in zip(preds, labels):
        jump = False
        for i, x in enumerate(pred, 1):
            if x in label:
                for k, cutoff in enumerate(cutoffs):
                    if i <= cutoff:
                        mrrs[k] += 1 / i
                jump = True
            if jump:
                break
    mrrs /= len(preds)
    for i, cutoff in enumerate(cutoffs):
        mrr = mrrs[i]
        metrics[f"MRR@{cutoff}"] = mrr

    # Recall
    recalls = np.zeros(len(cutoffs))
    for pred, label in zip(preds, labels):
        for k, cutoff in enumerate(cutoffs):
            recall = np.intersect1d(label, pred[:cutoff])
            recalls[k] += len(recall) / len(label)
    recalls /= len(preds)
    for i, cutoff in enumerate(cutoffs):
        recall = recalls[i]
        metrics[f"Recall@{cutoff}"] = recall

    # Precision
    precisions = np.zeros(len(cutoffs))
    for pred, label in zip(preds, labels):
        for k, cutoff in enumerate(cutoffs):
            precision = np.intersect1d(label, pred[:cutoff])
            precisions[k] += len(precision) / cutoff
    precisions /= len(preds)
    for i, cutoff in enumerate(cutoffs):
        precision = precisions[i]
        metrics[f"Precision@{cutoff}"] = precision

    # F1-Score@K
    f1_scores = np.zeros(len(cutoffs))
    for pred, label in zip(preds, labels):
        for k, cutoff in enumerate(cutoffs):
            recall = np.intersect1d(label, pred[:cutoff])
            precision = np.intersect1d(label, pred[:cutoff])
            recall_value = len(recall) / len(label)
            precision_value = len(precision) / cutoff
            if precision_value + recall_value > 0:
                f1_score = 2 * (precision_value * recall_value) / (precision_value + recall_value)
            else:
                f1_score = 0.0
            f1_scores[k] += f1_score
    f1_scores /= len(preds)
    for i, cutoff in enumerate(cutoffs):
        f1_score = f1_scores[i]
        metrics[f"F1-Score@{cutoff}"] = f1_score

    # Hit Rate
    hit_rates = np.zeros(len(cutoffs))
    for pred, label in zip(preds, labels):
        for k, cutoff in enumerate(cutoffs):
            hit = np.intersect1d(label, pred[:cutoff])
            if len(hit) > 0:
                hit_rates[k] += 1
    hit_rates /= len(preds)
    for i, cutoff in enumerate(cutoffs):
        hit_rate = hit_rates[i]
        metrics[f"HitRate@{cutoff}"] = hit_rate

    # NDCG
    ndcgs = np.zeros(len(cutoffs))
    for pred, label in zip(preds, labels):
        for k, cutoff in enumerate(cutoffs):
            pred_cutoff = pred[:cutoff]
            dcg = 0.0
            idcg = 0.0
            for i, item in enumerate(pred_cutoff, 1):
                if item in label:
                    dcg += 1.0 / np.log2(i + 1)
            for i in range(1, len(label) + 1):
                idcg += 1.0 / np.log2(i + 1)
            if idcg == 0:
                ndcgs[k] += 0
            else:
                ndcgs[k] += dcg / idcg
    ndcgs /= len(preds)
    for i, cutoff in enumerate(cutoffs):
        ndcg = ndcgs[i]
        metrics[f"NDCG@{cutoff}"] = ndcg

    return metrics
def main():
    parser = HfArgumentParser([Args])
    args: Args = parser.parse_args_into_dataclasses()[0]

    with open(args.test_data, "r") as f:
        test_data = json.load(f)
    # print(json.dumps(test_data, indent=4, ensure_ascii=False))
    # print(json.dumps(test_data, indent=4, ensure_ascii=False))
    corpus = test_data['corpus']
    test_data = test_data['test_data']

    model = FlagModel(
        args.encoder,
        query_instruction_for_retrieval="Represent this sentence for searching relevant passages: " if args.add_instruction else None,
        use_fp16=args.fp16
    )

    faiss_index = index(
        model=model,
        corpus=corpus,
        batch_size=args.batch_size,
        max_length=args.max_passage_length,
        index_factory=args.index_factory,
        save_path=args.save_path,
        save_embedding=args.save_embedding,
        load_embedding=args.load_embedding
    )

    scores, indices = search(
        model=model,
        queries=test_data,
        faiss_index=faiss_index,
        k=args.k,
        batch_size=args.batch_size,
        max_length=args.max_query_length
    )
    retrieval_results = []
    for indice in indices:
        # filter invalid indices
        indice = indice[indice != -1].tolist()
        conts = []
        for ind in indice:
            conts.append(corpus['content'][ind])
        retrieval_results.append(conts)
    # print(retrieval_results)
    ground_truths = []
    for sample in test_data['query']:
        ground_truths.append(test_data['mapper'][sample])
    metrics = evaluate(retrieval_results, ground_truths)
    for k, v in metrics.items():
        print('{'+f"\"{k}\": {v:.4f}"+'}')


if __name__ == "__main__":
    main()
