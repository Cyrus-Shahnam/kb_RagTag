# -*- coding: utf-8 -*-
import os
import time
import shutil
import unittest
from configparser import ConfigParser

from kb_ragtag.kb_ragtagImpl import kb_ragtag
from kb_ragtag.kb_ragtagServer import MethodContext
from kb_ragtag.authclient import KBaseAuth as _KBaseAuth

from installed_clients.WorkspaceClient import Workspace
from installed_clients.AssemblyUtilClient import AssemblyUtil


class kb_ragtagTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        token = os.environ.get('KB_AUTH_TOKEN', None)
        config_file = os.environ.get('KB_DEPLOYMENT_CONFIG', None)
        cls.cfg = {}
        config = ConfigParser()
        config.read(config_file)
        for nameval in config.items('kb_ragtag'):
            cls.cfg[nameval[0]] = nameval[1]
        # Getting username from Auth profile for token
        authServiceUrl = cls.cfg['auth-service-url']
        auth_client = _KBaseAuth(authServiceUrl)
        user_id = auth_client.get_user(token)
        # WARNING: don't call any logging methods on the context object,
        # it'll result in a NoneType error
        cls.ctx = MethodContext(None)
        cls.ctx.update({'token': token,
                        'user_id': user_id,
                        'provenance': [
                            {'service': 'kb_ragtag',
                             'method': 'please_never_use_it_in_production',
                             'method_params': []
                             }],
                        'authenticated': 1})
        cls.wsURL = cls.cfg['workspace-url']
        cls.wsClient = Workspace(cls.wsURL)
        cls.serviceImpl = kb_ragtag(cls.cfg)
        cls.scratch = cls.cfg['scratch']
        cls.callback_url = os.environ['SDK_CALLBACK_URL']
        suffix = int(time.time() * 1000)
        cls.wsName = "test_kb_ragtag_" + str(suffix)
        cls.wsClient.create_workspace({'workspace': cls.wsName})

        cls.au = AssemblyUtil(cls.callback_url)
        cls.test_data_dir = os.path.join(os.path.dirname(__file__), 'data')

        # Stage all input assemblies once for the whole test class.
        cls.ref_ref = cls._load_assembly('ref.fasta', 'ref_assembly')
        cls.ref2_ref = cls._load_assembly('ref2.fasta', 'ref2_assembly')
        cls.query_frag_ref = cls._load_assembly(
            'query_fragments.fasta', 'query_fragments')
        cls.query_mis_ref = cls._load_assembly(
            'query_misassembled.fasta', 'query_misassembled')
        cls.target_ref = cls._load_assembly(
            'target_fragmented.fasta', 'target_fragmented')

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'wsName'):
            cls.wsClient.delete_workspace({'workspace': cls.wsName})
            print('Test workspace was deleted')

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    @classmethod
    def _load_assembly(cls, fasta_name, obj_name):
        """Copy a bundled FASTA into scratch (so the AssemblyUtil container can
        read it) and save it as an Assembly object; return its workspace ref."""
        src = os.path.join(cls.test_data_dir, fasta_name)
        dst = os.path.join(cls.scratch, fasta_name)
        shutil.copy(src, dst)
        ref = cls.au.save_assembly_from_fasta({
            'file': {'path': dst},
            'workspace_name': cls.wsName,
            'assembly_name': obj_name,
        })
        if isinstance(ref, dict):
            ref = ref.get('assembly_ref') or ref.get('ref')
        return ref

    def _assert_ok(self, output, out_name):
        """Every app returns report_name/report_ref + output_assembly_ref, and
        the named Assembly object should now exist in the workspace."""
        self.assertIn('report_name', output)
        self.assertIn('report_ref', output)
        self.assertTrue(output.get('report_ref'))
        self.assertIn('output_assembly_ref', output)
        self.assertTrue(output.get('output_assembly_ref'))
        info = self.wsClient.get_object_info3(
            {'objects': [{'ref': output['output_assembly_ref']}]})
        obj_info = info['infos'][0]
        self.assertEqual(obj_info[1], out_name)                 # object name
        self.assertIn('KBaseGenomeAnnotations.Assembly', obj_info[2])  # type

    # ------------------------------------------------------------------ #
    # one smoke test per app
    # ------------------------------------------------------------------ #
    def test_01_scaffold(self):
        out = self.serviceImpl.run_ragtag_scaffold(self.ctx, {
            'workspace_name': self.wsName,
            'reference_assembly_ref': self.ref_ref,
            'query_assembly_ref': self.query_frag_ref,
            'output_assembly_name': 'scaffold_out',
            'aligner': 'minimap2',
            'threads': 2,
        })[0]
        self._assert_ok(out, 'scaffold_out')

    def test_02_correct(self):
        out = self.serviceImpl.run_ragtag_correct(self.ctx, {
            'workspace_name': self.wsName,
            'reference_assembly_ref': self.ref_ref,
            'query_assembly_ref': self.query_mis_ref,
            'output_assembly_name': 'correct_out',
            'aligner': 'minimap2',
            'threads': 2,
        })[0]
        self._assert_ok(out, 'correct_out')

    def test_03_patch(self):
        out = self.serviceImpl.run_ragtag_patch(self.ctx, {
            'workspace_name': self.wsName,
            'target_assembly_ref': self.target_ref,
            'query_assembly_ref': self.ref_ref,
            'output_assembly_name': 'patch_out',
            'aligner': 'nucmer',
            'threads': 2,
        })[0]
        self._assert_ok(out, 'patch_out')

    def test_04_merge(self):
        out = self.serviceImpl.run_ragtag_merge(self.ctx, {
            'workspace_name': self.wsName,
            'query_assembly_ref': self.query_frag_ref,
            'reference_assembly_refs': [self.ref_ref, self.ref2_ref],
            'output_assembly_name': 'merge_out',
            'aligner': 'minimap2',
            'threads': 2,
        })[0]
        self._assert_ok(out, 'merge_out')

    def test_05_missing_param_raises(self):
        """A required parameter omission should raise (fast, no tool run)."""
        with self.assertRaises(ValueError):
            self.serviceImpl.run_ragtag_scaffold(self.ctx, {
                'workspace_name': self.wsName,
                'reference_assembly_ref': self.ref_ref,
                # query_assembly_ref intentionally missing
                'output_assembly_name': 'should_fail',
            })
