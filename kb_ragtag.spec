/*
A KBase module: kb_ragtag

Wraps RagTag (https://github.com/malonge/RagTag) for reference-guided
genome assembly scaffolding and improvement. Exposes four apps:

  correct  - break a query assembly at putative misassemblies
  scaffold - order/orient query contigs against a reference
  patch    - fill gaps / join a target assembly using a query assembly
  merge    - reconcile multiple reference-guided scaffoldings into a consensus
*/
module kb_ragtag {

    /* A reference to an Assembly object (KBaseGenomeAnnotations.Assembly) */
    typedef string assembly_ref;

    /* Common return type for every app:
       report_name / report_ref  - the KBaseReport
       output_assembly_ref        - the new Assembly object produced */
    typedef structure {
        string report_name;
        string report_ref;
        assembly_ref output_assembly_ref;
    } RagTagResults;

    /*
        correct: break query sequences at reference-discordant misassemblies.
        break_mode    - '', 'inter', or 'intra' (--inter / --intra)
        min_break_dist - (-b) minimum break distance from contig ends
    */
    typedef structure {
        string workspace_name;
        assembly_ref reference_assembly_ref;
        assembly_ref query_assembly_ref;
        string output_assembly_name;
        string aligner;
        int threads;
        int min_unique_len;
        int min_break_dist;
        string break_mode;
    } CorrectParams;

    funcdef run_ragtag_correct(CorrectParams params)
        returns (RagTagResults output) authentication required;

    /*
        scaffold: order and orient query contigs against a reference.
        concat_unplaced - (-C) concatenate unplaced contigs into 'Chr0' (0/1)
        infer_gaps      - (-r) infer gap sizes instead of fixed 100bp (0/1)
    */
    typedef structure {
        string workspace_name;
        assembly_ref reference_assembly_ref;
        assembly_ref query_assembly_ref;
        string output_assembly_name;
        string aligner;
        int threads;
        int min_unique_len;
        int concat_unplaced;
        int infer_gaps;
    } ScaffoldParams;

    funcdef run_ragtag_scaffold(ScaffoldParams params)
        returns (RagTagResults output) authentication required;

    /*
        patch: fill gaps and/or join sequences in target using query.
        patch_mode - '', 'fill_only' (--fill-only), or 'join_only' (--join-only)
        Note: patch defaults to the nucmer aligner.
    */
    typedef structure {
        string workspace_name;
        assembly_ref target_assembly_ref;
        assembly_ref query_assembly_ref;
        string output_assembly_name;
        string aligner;
        int threads;
        int min_unique_len;
        string patch_mode;
    } PatchParams;

    funcdef run_ragtag_patch(PatchParams params)
        returns (RagTagResults output) authentication required;

    /*
        merge: reconcile multiple reference-guided scaffoldings.
        The query is scaffolded against each reference (>= 2 required) to
        generate AGP files, which are then merged into a consensus.
        min_edge_weight - (-e) minimum edge weight to keep a join
        gap_func        - (--gap-func) 'min', 'max', or 'mean'
    */
    typedef structure {
        string workspace_name;
        assembly_ref query_assembly_ref;
        list<assembly_ref> reference_assembly_refs;
        string output_assembly_name;
        string aligner;
        int threads;
        float min_edge_weight;
        string gap_func;
    } MergeParams;

    funcdef run_ragtag_merge(MergeParams params)
        returns (RagTagResults output) authentication required;
};
