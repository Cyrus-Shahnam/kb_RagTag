#!/usr/bin/env python3
"""
Generate small, reproducible FASTA inputs for the kb_ragtag tests.

Everything is derived from a single simulated 2-chromosome "reference" genome
so the alignments RagTag needs are exact and deterministic (fixed seed). This
keeps `kb-sdk test` fast and self-contained (no network, no external workspace
refs, which the KBase docs warn against).

Files produced (in this directory):
    ref.fasta                 reference genome (2 seqs) -> scaffold/correct ref,
                              and reused as the patch "query" (complete) assembly
    ref2.fasta                lightly mutated reference -> 2nd reference for merge
    query_fragments.fasta     ref cut into shuffled/RC contigs -> scaffold + merge query
    query_misassembled.fasta  contigs incl. one chr1+chr2 chimera -> correct query
    target_fragmented.fasta   two ref regions with a gap between -> patch target

To use REAL public data instead (heavier, more realistic), see README.md in
this directory: download a genome (e.g. E. coli K-12 MG1655, GenBank U00096.3),
save it as ref.fasta, and re-run this script -- the derived files rebuild from
whatever ref.fasta contains.
"""

import os
import random

SEED = 42
HERE = os.path.dirname(os.path.abspath(__file__))
BASES = "ACGT"
COMP = str.maketrans("ACGTacgt", "TGCAtgca")


def rand_seq(n, rng):
    return "".join(rng.choice(BASES) for _ in range(n))


def revcomp(s):
    return s.translate(COMP)[::-1]


def write_fasta(path, records, width=70):
    with open(path, "w") as fh:
        for name, seq in records:
            fh.write(">" + name + "\n")
            for i in range(0, len(seq), width):
                fh.write(seq[i:i + width] + "\n")


def read_fasta(path):
    records, name, buf = [], None, []
    with open(path) as fh:
        for line in fh:
            line = line.rstrip()
            if line.startswith(">"):
                if name is not None:
                    records.append((name, "".join(buf)))
                name, buf = line[1:].split()[0], []
            else:
                buf.append(line)
    if name is not None:
        records.append((name, "".join(buf)))
    return records


def fragment(seq, rng, n_pieces, gap=500):
    """Cut a sequence into n_pieces contigs, dropping a small gap between them."""
    L = len(seq)
    # random-ish but sorted breakpoints
    cuts = sorted(rng.sample(range(gap * 2, L - gap * 2), n_pieces - 1))
    bounds = [0] + cuts + [L]
    pieces = []
    for i in range(len(bounds) - 1):
        start = bounds[i] + (gap if i > 0 else 0)
        end = bounds[i + 1]
        if end - start > gap:
            pieces.append(seq[start:end])
    return pieces


def main():
    rng = random.Random(SEED)

    # ---- 1) reference genome: two chromosomes ---------------------------
    if os.path.exists(os.path.join(HERE, "ref.fasta")):
        ref = read_fasta(os.path.join(HERE, "ref.fasta"))
        print("Using existing ref.fasta as the source genome")
    else:
        chr1 = rand_seq(80000, rng)
        chr2 = rand_seq(60000, rng)
        ref = [("sim_chr1", chr1), ("sim_chr2", chr2)]
        write_fasta(os.path.join(HERE, "ref.fasta"), ref)
        print("Wrote ref.fasta (sim_chr1 80kb, sim_chr2 60kb)")

    seqs = dict(ref)
    chr1 = seqs[ref[0][0]]
    chr2 = seqs[ref[1][0]] if len(ref) > 1 else seqs[ref[0][0]]

    # ---- 2) ref2: lightly mutated copy (for merge) ----------------------
    def mutate(seq, rate=0.001):
        s = list(seq)
        for i in range(len(s)):
            if rng.random() < rate:
                s[i] = rng.choice(BASES)
        return "".join(s)

    ref2 = [(name + "_v2", mutate(seq)) for name, seq in ref]
    write_fasta(os.path.join(HERE, "ref2.fasta"), ref2)

    # ---- 3) query_fragments: shuffled + RC contigs (scaffold/merge) -----
    pieces = []
    for name, seq in ref:
        pieces.extend(fragment(seq, rng, n_pieces=(5 if name == ref[0][0] else 4)))
    rng.shuffle(pieces)
    frags = []
    for i, p in enumerate(pieces):
        if rng.random() < 0.5:
            p = revcomp(p)
        frags.append(("contig_%02d" % (i + 1), p))
    write_fasta(os.path.join(HERE, "query_fragments.fasta"), frags)

    # ---- 4) query_misassembled: one chr1+chr2 chimera (correct) ---------
    chimera = chr1[:15000] + chr2[:15000]          # inter-chromosome misjoin
    normal_a = chr1[20000:45000]
    normal_b = chr2[20000:50000]
    mis = [
        ("misjoin_contig", chimera),
        ("good_contig_1", normal_a),
        ("good_contig_2", normal_b),
    ]
    write_fasta(os.path.join(HERE, "query_misassembled.fasta"), mis)

    # ---- 5) target_fragmented: two chr1 regions with a gap (patch) ------
    target = [
        ("target_left",  chr1[20000:49000]),
        ("target_right", chr1[51000:80000]),        # 2kb gap (49k-51k) missing
    ]
    write_fasta(os.path.join(HERE, "target_fragmented.fasta"), target)

    # ---- summary --------------------------------------------------------
    for fn in ["ref.fasta", "ref2.fasta", "query_fragments.fasta",
               "query_misassembled.fasta", "target_fragmented.fasta"]:
        recs = read_fasta(os.path.join(HERE, fn))
        total = sum(len(s) for _, s in recs)
        print("%-26s %2d seqs, %7d bp" % (fn, len(recs), total))


if __name__ == "__main__":
    main()
