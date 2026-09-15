# -*- coding: utf-8 -*-
#BEGIN_HEADER
from kb_ragtag.ragtag_utils import RagTagRunner
#END_HEADER


class kb_ragtag:
    '''
    Module Name:
    kb_ragtag

    Module Description:
    A KBase module: kb_ragtag

Wraps RagTag (https://github.com/malonge/RagTag) for reference-guided
genome assembly scaffolding and improvement. Exposes four apps:

  correct  - break a query assembly at putative misassemblies
  scaffold - order/orient query contigs against a reference
  patch    - fill gaps / join a target assembly using a query assembly
  merge    - reconcile multiple reference-guided scaffoldings into a consensus
    '''

    ######## WARNING FOR GEVENT USERS ####### noqa
    # Since asynchronous IO can lead to methods - even the same method -
    # interrupting each other, you must be *very* careful when using global
    # state. A method could easily clobber the state set by another while
    # the latter method is running.
    ######################################### noqa
    VERSION = "0.0.1"
    GIT_URL = ""
    GIT_COMMIT_HASH = ""

    #BEGIN_CLASS_HEADER
    #END_CLASS_HEADER

    # config contains contents of config file in a hash or None if it couldn't
    # be found
    def __init__(self, config):
        #BEGIN_CONSTRUCTOR
        self.config = config
        #END_CONSTRUCTOR
        pass


    def run_ragtag_correct(self, ctx, params):
        """
        :param params: instance of type "CorrectParams" (correct: break query
           sequences at reference-discordant misassemblies. break_mode    -
           '', 'inter', or 'intra' (--inter / --intra) min_break_dist - (-b)
           minimum break distance from contig ends) -> structure: parameter
           "workspace_name" of String, parameter "reference_assembly_ref" of
           type "assembly_ref" (A reference to an Assembly object
           (KBaseGenomeAnnotations.Assembly)), parameter "query_assembly_ref"
           of type "assembly_ref" (A reference to an Assembly object
           (KBaseGenomeAnnotations.Assembly)), parameter
           "output_assembly_name" of String, parameter "aligner" of String,
           parameter "threads" of Long, parameter "min_unique_len" of Long,
           parameter "min_break_dist" of Long, parameter "break_mode" of
           String
        :returns: instance of type "RagTagResults" (Common return type for
           every app: report_name / report_ref  - the KBaseReport
           output_assembly_ref        - the new Assembly object produced) ->
           structure: parameter "report_name" of String, parameter
           "report_ref" of String, parameter "output_assembly_ref" of type
           "assembly_ref" (A reference to an Assembly object
           (KBaseGenomeAnnotations.Assembly))
        """
        # ctx is the context object
        # return variables are: output
        #BEGIN run_ragtag_correct
        output = RagTagRunner(self.config).correct(params)
        #END run_ragtag_correct

        # At some point might do deeper type checking...
        if not isinstance(output, dict):
            raise ValueError('Method run_ragtag_correct return value ' +
                             'output is not type dict as required.')
        # return the results
        return [output]

    def run_ragtag_scaffold(self, ctx, params):
        """
        :param params: instance of type "ScaffoldParams" (scaffold: order and
           orient query contigs against a reference. concat_unplaced - (-C)
           concatenate unplaced contigs into 'Chr0' (0/1) infer_gaps      -
           (-r) infer gap sizes instead of fixed 100bp (0/1)) -> structure:
           parameter "workspace_name" of String, parameter
           "reference_assembly_ref" of type "assembly_ref" (A reference to an
           Assembly object (KBaseGenomeAnnotations.Assembly)), parameter
           "query_assembly_ref" of type "assembly_ref" (A reference to an
           Assembly object (KBaseGenomeAnnotations.Assembly)), parameter
           "output_assembly_name" of String, parameter "aligner" of String,
           parameter "threads" of Long, parameter "min_unique_len" of Long,
           parameter "concat_unplaced" of Long, parameter "infer_gaps" of Long
        :returns: instance of type "RagTagResults" (Common return type for
           every app: report_name / report_ref  - the KBaseReport
           output_assembly_ref        - the new Assembly object produced) ->
           structure: parameter "report_name" of String, parameter
           "report_ref" of String, parameter "output_assembly_ref" of type
           "assembly_ref" (A reference to an Assembly object
           (KBaseGenomeAnnotations.Assembly))
        """
        # ctx is the context object
        # return variables are: output
        #BEGIN run_ragtag_scaffold
        output = RagTagRunner(self.config).scaffold(params)
        #END run_ragtag_scaffold

        # At some point might do deeper type checking...
        if not isinstance(output, dict):
            raise ValueError('Method run_ragtag_scaffold return value ' +
                             'output is not type dict as required.')
        # return the results
        return [output]

    def run_ragtag_patch(self, ctx, params):
        """
        :param params: instance of type "PatchParams" (patch: fill gaps
           and/or join sequences in target using query. patch_mode - '',
           'fill_only' (--fill-only), or 'join_only' (--join-only) Note:
           patch defaults to the nucmer aligner.) -> structure: parameter
           "workspace_name" of String, parameter "target_assembly_ref" of
           type "assembly_ref" (A reference to an Assembly object
           (KBaseGenomeAnnotations.Assembly)), parameter "query_assembly_ref"
           of type "assembly_ref" (A reference to an Assembly object
           (KBaseGenomeAnnotations.Assembly)), parameter
           "output_assembly_name" of String, parameter "aligner" of String,
           parameter "threads" of Long, parameter "min_unique_len" of Long,
           parameter "patch_mode" of String
        :returns: instance of type "RagTagResults" (Common return type for
           every app: report_name / report_ref  - the KBaseReport
           output_assembly_ref        - the new Assembly object produced) ->
           structure: parameter "report_name" of String, parameter
           "report_ref" of String, parameter "output_assembly_ref" of type
           "assembly_ref" (A reference to an Assembly object
           (KBaseGenomeAnnotations.Assembly))
        """
        # ctx is the context object
        # return variables are: output
        #BEGIN run_ragtag_patch
        output = RagTagRunner(self.config).patch(params)
        #END run_ragtag_patch

        # At some point might do deeper type checking...
        if not isinstance(output, dict):
            raise ValueError('Method run_ragtag_patch return value ' +
                             'output is not type dict as required.')
        # return the results
        return [output]

    def run_ragtag_merge(self, ctx, params):
        """
        :param params: instance of type "MergeParams" (merge: reconcile
           multiple reference-guided scaffoldings. The query is scaffolded
           against each reference (>= 2 required) to generate AGP files,
           which are then merged into a consensus. min_edge_weight - (-e)
           minimum edge weight to keep a join gap_func        - (--gap-func)
           'min', 'max', or 'mean') -> structure: parameter "workspace_name"
           of String, parameter "query_assembly_ref" of type "assembly_ref"
           (A reference to an Assembly object
           (KBaseGenomeAnnotations.Assembly)), parameter
           "reference_assembly_refs" of list of type "assembly_ref" (A
           reference to an Assembly object
           (KBaseGenomeAnnotations.Assembly)), parameter
           "output_assembly_name" of String, parameter "aligner" of String,
           parameter "threads" of Long, parameter "min_edge_weight" of
           Double, parameter "gap_func" of String
        :returns: instance of type "RagTagResults" (Common return type for
           every app: report_name / report_ref  - the KBaseReport
           output_assembly_ref        - the new Assembly object produced) ->
           structure: parameter "report_name" of String, parameter
           "report_ref" of String, parameter "output_assembly_ref" of type
           "assembly_ref" (A reference to an Assembly object
           (KBaseGenomeAnnotations.Assembly))
        """
        # ctx is the context object
        # return variables are: output
        #BEGIN run_ragtag_merge
        output = RagTagRunner(self.config).merge(params)
        #END run_ragtag_merge

        # At some point might do deeper type checking...
        if not isinstance(output, dict):
            raise ValueError('Method run_ragtag_merge return value ' +
                             'output is not type dict as required.')
        # return the results
        return [output]
    def status(self, ctx):
        #BEGIN_STATUS
        returnVal = {'state': "OK",
                     'message': "",
                     'version': self.VERSION,
                     'git_url': self.GIT_URL,
                     'git_commit_hash': self.GIT_COMMIT_HASH}
        #END_STATUS
        return [returnVal]
