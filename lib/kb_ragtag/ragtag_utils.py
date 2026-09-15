# -*- coding: utf-8 -*-
"""
Shared logic for the kb_ragtag module.

Each of the four KBase apps (scaffold, correct, patch, merge) is a thin
wrapper in kb_ragtagImpl.py that delegates to a method here. Keeping the
logic in this module (rather than inside the SDK-managed Impl file) means
it is never touched by `make` / code regeneration.

The recurring pattern for every command is the same:
    1. download input Assembly object(s) to FASTA       (AssemblyUtil)
    2. run the ragtag.py subcommand                       (subprocess)
    3. save the resulting FASTA back as a new Assembly     (AssemblyUtil)
    4. build a KBaseReport with the AGP/stats file links   (KBaseReport)

RagTag lives in a dedicated micromamba env at /opt/conda/envs/ragtag (see the
Dockerfile). The image PATH is deliberately left untouched so the conda Python
never shadows the KBase server Python; instead we invoke ragtag.py by absolute
path and prepend the env's bin dir onto PATH *only for the RagTag subprocess*
(RAGTAG_ENV_BIN), which lets nucmer find its helper binaries at runtime.
"""

import os
import subprocess
import uuid

from installed_clients.AssemblyUtilClient import AssemblyUtil
from installed_clients.KBaseReportClient import KBaseReport

# Location of the RagTag conda env; overridable for local testing.
RAGTAG_ENV_BIN = os.environ.get('RAGTAG_ENV_BIN', '/opt/conda/envs/ragtag/bin')
RAGTAG = os.path.join(RAGTAG_ENV_BIN, 'ragtag.py')


class RagTagRunner(object):

    def __init__(self, config):
        self.callback_url = os.environ['SDK_CALLBACK_URL']
        self.scratch = config['scratch']
        self.au = AssemblyUtil(self.callback_url)

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    def _new_workdir(self):
        run_id = str(uuid.uuid4())
        work_dir = os.path.join(self.scratch, 'ragtag_' + run_id)
        os.makedirs(work_dir, exist_ok=True)
        return run_id, work_dir

    def _fasta(self, ref):
        """Download an Assembly object to a local FASTA, return its path."""
        return self.au.get_assembly_as_fasta({'ref': ref})['path']

    def _run(self, cmd, cwd):
        printable = ' '.join(str(c) for c in cmd)
        print('Running: ' + printable)
        # Prepend the RagTag env bin onto PATH for this subprocess only, so
        # ragtag.py and (critically) nucmer's helper binaries resolve, without
        # altering the image / server PATH.
        env = dict(os.environ)
        env['PATH'] = RAGTAG_ENV_BIN + os.pathsep + env.get('PATH', '')
        proc = subprocess.run(
            cmd, cwd=cwd, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            universal_newlines=True)
        print(proc.stdout)
        if proc.returncode != 0:
            raise RuntimeError(
                'RagTag command failed (exit code {}): {}\nSee log above.'
                .format(proc.returncode, printable))
        return proc.stdout

    def _save_assembly(self, fasta_path, workspace_name, assembly_name):
        ref = self.au.save_assembly_from_fasta({
            'file': {'path': fasta_path},
            'workspace_name': workspace_name,
            'assembly_name': assembly_name,
        })
        # depending on AssemblyUtil version this is a ref string or a dict
        if isinstance(ref, dict):
            ref = ref.get('assembly_ref') or ref.get('ref')
        return ref

    def _file_links(self, out_dir, names):
        links = []
        for name in names:
            path = os.path.join(out_dir, name)
            if os.path.exists(path):
                links.append({
                    'path': path,
                    'name': name,
                    'description': 'RagTag output: ' + name,
                })
        return links

    def _report(self, workspace_name, run_id, message,
                new_ref, description, file_links):
        report = KBaseReport(self.callback_url)
        info = report.create_extended_report({
            'message': message,
            'objects_created': [{'ref': new_ref, 'description': description}],
            'file_links': file_links,
            'report_object_name': 'kb_ragtag_report_' + run_id,
            'workspace_name': workspace_name,
        })
        return {'report_name': info['name'], 'report_ref': info['ref']}

    @staticmethod
    def _require(params, keys):
        for key in keys:
            if not params.get(key):
                raise ValueError(
                    'Required parameter "{}" is missing'.format(key))

    @staticmethod
    def _check(path):
        if not os.path.exists(path):
            raise RuntimeError('Expected output not found: ' + path)

    @staticmethod
    def _aligner_path(params, default_aligner):
        """Absolute path to the chosen aligner inside the RagTag env."""
        return os.path.join(RAGTAG_ENV_BIN, params.get('aligner') or default_aligner)

    @classmethod
    def _align_opts(cls, params, default_aligner):
        cmd = ['-t', str(int(params.get('threads') or 4)),
               '--aligner', cls._aligner_path(params, default_aligner)]
        if params.get('min_unique_len'):
            cmd += ['-f', str(int(params['min_unique_len']))]
        return cmd

    # ------------------------------------------------------------------ #
    # scaffold
    # ------------------------------------------------------------------ #
    def scaffold(self, params):
        self._require(params, ['workspace_name', 'reference_assembly_ref',
                               'query_assembly_ref', 'output_assembly_name'])
        run_id, work_dir = self._new_workdir()
        out_dir = os.path.join(work_dir, 'output')

        ref = self._fasta(params['reference_assembly_ref'])
        qry = self._fasta(params['query_assembly_ref'])

        cmd = [RAGTAG, 'scaffold', ref, qry, '-o', out_dir, '-w']
        cmd += self._align_opts(params, 'minimap2')
        if int(params.get('concat_unplaced') or 0) == 1:
            cmd += ['-C']
        if int(params.get('infer_gaps') or 0) == 1:
            cmd += ['-r']
        self._run(cmd, work_dir)

        fasta = os.path.join(out_dir, 'ragtag.scaffold.fasta')
        self._check(fasta)
        new_ref = self._save_assembly(
            fasta, params['workspace_name'], params['output_assembly_name'])

        stats_path = os.path.join(out_dir, 'ragtag.scaffold.stats')
        stats = ''
        if os.path.exists(stats_path):
            with open(stats_path) as fh:
                stats = fh.read()
        links = self._file_links(out_dir, [
            'ragtag.scaffold.agp', 'ragtag.scaffold.stats',
            'ragtag.scaffold.confidence.txt'])

        out = self._report(
            params['workspace_name'], run_id,
            'RagTag scaffolding complete.\n\n' + stats,
            new_ref, 'Scaffolded assembly (RagTag)', links)
        out['output_assembly_ref'] = new_ref
        return out

    # ------------------------------------------------------------------ #
    # correct
    # ------------------------------------------------------------------ #
    def correct(self, params):
        self._require(params, ['workspace_name', 'reference_assembly_ref',
                               'query_assembly_ref', 'output_assembly_name'])
        run_id, work_dir = self._new_workdir()
        out_dir = os.path.join(work_dir, 'output')

        ref = self._fasta(params['reference_assembly_ref'])
        qry = self._fasta(params['query_assembly_ref'])

        cmd = [RAGTAG, 'correct', ref, qry, '-o', out_dir, '-w']
        cmd += self._align_opts(params, 'minimap2')
        if params.get('min_break_dist'):
            cmd += ['-b', str(int(params['min_break_dist']))]
        break_mode = params.get('break_mode')
        if break_mode == 'inter':
            cmd += ['--inter']
        elif break_mode == 'intra':
            cmd += ['--intra']
        self._run(cmd, work_dir)

        fasta = os.path.join(out_dir, 'ragtag.correct.fasta')
        self._check(fasta)
        new_ref = self._save_assembly(
            fasta, params['workspace_name'], params['output_assembly_name'])

        links = self._file_links(out_dir, ['ragtag.correct.agp'])
        out = self._report(
            params['workspace_name'], run_id,
            'RagTag correction complete. Query sequences were broken at '
            'putative misassemblies (sequence is never added or removed).',
            new_ref, 'Corrected assembly (RagTag)', links)
        out['output_assembly_ref'] = new_ref
        return out

    # ------------------------------------------------------------------ #
    # patch
    # ------------------------------------------------------------------ #
    def patch(self, params):
        self._require(params, ['workspace_name', 'target_assembly_ref',
                               'query_assembly_ref', 'output_assembly_name'])
        run_id, work_dir = self._new_workdir()
        out_dir = os.path.join(work_dir, 'output')

        target = self._fasta(params['target_assembly_ref'])
        qry = self._fasta(params['query_assembly_ref'])

        # patch defaults to nucmer per the RagTag docs
        cmd = [RAGTAG, 'patch', target, qry, '-o', out_dir, '-w']
        cmd += self._align_opts(params, 'nucmer')
        patch_mode = params.get('patch_mode')
        if patch_mode == 'fill_only':
            cmd += ['--fill-only']
        elif patch_mode == 'join_only':
            cmd += ['--join-only']
        self._run(cmd, work_dir)

        fasta = os.path.join(out_dir, 'ragtag.patch.fasta')
        self._check(fasta)
        new_ref = self._save_assembly(
            fasta, params['workspace_name'], params['output_assembly_name'])

        links = self._file_links(out_dir, ['ragtag.patch.agp'])
        out = self._report(
            params['workspace_name'], run_id,
            'RagTag patching complete. Gaps were filled and/or target '
            'sequences joined using the query assembly.',
            new_ref, 'Patched assembly (RagTag)', links)
        out['output_assembly_ref'] = new_ref
        return out

    # ------------------------------------------------------------------ #
    # merge
    # ------------------------------------------------------------------ #
    def merge(self, params):
        """
        KBase-native merge: instead of asking users for AGP files (not a
        native type), accept the query assembly plus >= 2 reference
        assemblies. We scaffold the query against each reference to produce
        one AGP per reference, then reconcile them with `ragtag.py merge`.
        """
        self._require(params, ['workspace_name', 'query_assembly_ref',
                               'reference_assembly_refs',
                               'output_assembly_name'])
        refs = params['reference_assembly_refs']
        if not isinstance(refs, list) or len(refs) < 2:
            raise ValueError(
                'merge requires at least 2 reference assemblies so that there '
                'are at least 2 scaffoldings to reconcile.')

        run_id, work_dir = self._new_workdir()
        qry = self._fasta(params['query_assembly_ref'])
        aligner_path = self._aligner_path(params, 'minimap2')
        threads = str(int(params.get('threads') or 4))

        # 1) scaffold the query against each reference -> one AGP each
        agp_files = []
        for i, rref in enumerate(refs):
            rfasta = self._fasta(rref)
            sdir = os.path.join(work_dir, 'scaffold_{}'.format(i))
            scmd = [RAGTAG, 'scaffold', rfasta, qry,
                    '-o', sdir, '-w', '-t', threads, '--aligner', aligner_path]
            self._run(scmd, work_dir)
            agp = os.path.join(sdir, 'ragtag.scaffold.agp')
            self._check(agp)
            agp_files.append(agp)

        # 2) reconcile the AGPs into a consensus
        mdir = os.path.join(work_dir, 'merge_output')
        mcmd = [RAGTAG, 'merge', qry] + agp_files + ['-o', mdir, '-w']
        if params.get('min_edge_weight') not in (None, ''):
            mcmd += ['-e', str(params['min_edge_weight'])]
        if params.get('gap_func'):
            mcmd += ['--gap-func', params['gap_func']]
        self._run(mcmd, work_dir)

        fasta = os.path.join(mdir, 'ragtag.merge.fasta')
        self._check(fasta)
        new_ref = self._save_assembly(
            fasta, params['workspace_name'], params['output_assembly_name'])

        links = self._file_links(mdir, ['ragtag.merge.agp'])
        out = self._report(
            params['workspace_name'], run_id,
            'RagTag merge complete. Reconciled {} reference-guided '
            'scaffoldings into a consensus assembly.'.format(len(refs)),
            new_ref, 'Merged consensus assembly (RagTag)', links)
        out['output_assembly_ref'] = new_ref
        return out
