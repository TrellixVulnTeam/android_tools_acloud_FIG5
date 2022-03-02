# Copyright 2022 - The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for remote_host_cf_device_factory."""

import unittest
from unittest import mock

from acloud.internal import constants
from acloud.internal.lib import auth
from acloud.internal.lib import driver_test_lib
from acloud.internal.lib import cvd_compute_client_multi_stage
from acloud.public.actions import remote_host_cf_device_factory

class RemoteHostDeviceFactoryTest(driver_test_lib.BaseDriverTest):
    """Test RemoteHostDeviceFactory."""

    def setUp(self):
        """Set up the test."""
        super().setUp()
        self.Patch(auth, "CreateCredentials")
        self.Patch(cvd_compute_client_multi_stage, "CvdComputeClient")

    @staticmethod
    def _CreateMockAvdSpec():
        """Create a mock AvdSpec with necessary attributes."""
        mock_cfg = mock.Mock(spec=[],
                             extra_data_disk_size_gb=10,
                             ssh_private_key_path="/mock/id_rsa",
                             extra_args_ssh_tunnel="extra args",
                             fetch_cvd_version="123456",
                             creds_cache_file="credential")
        return mock.Mock(spec=[],
                         remote_image={
                             "branch": "aosp-android12-gsi",
                             "build_id": "100000",
                             "build_target": "aosp_cf_x86_64_phone-userdebug"},
                         system_build_info={},
                         kernel_build_info={},
                         bootloader_build_info={},
                         ota_build_info={},
                         remote_host="192.0.2.100",
                         host_user="user1",
                         host_ssh_private_key_path=None,
                         report_internal_ip=False,
                         image_source=constants.IMAGE_SRC_REMOTE,
                         local_image_dir=None,
                         ins_timeout_secs=200,
                         boot_timeout_secs=100,
                         gpu="auto",
                         cfg=mock_cfg)

    @mock.patch("acloud.public.actions.remote_host_cf_device_factory."
                "cvd_compute_client_multi_stage")
    @mock.patch("acloud.public.actions.remote_host_cf_device_factory.ssh")
    @mock.patch("acloud.public.actions.remote_host_cf_device_factory."
                "cvd_utils")
    def testCreateInstanceWithImageDir(self, mock_cvd_utils, mock_ssh,
                                       _mock_client):
        """Test CreateInstance with local image directory."""
        mock_avd_spec = self._CreateMockAvdSpec()
        mock_avd_spec.image_source = constants.IMAGE_SRC_LOCAL
        mock_avd_spec.local_image_dir = "/mock/img"
        factory = remote_host_cf_device_factory.RemoteHostDeviceFactory(
            mock_avd_spec, cvd_host_package_artifact="/mock/cvd.tar.gz")

        mock_client_obj = factory.GetComputeClient()
        mock_client_obj.FormatRemoteHostInstanceName.return_value = "inst"
        mock_client_obj.LaunchCvd.return_value = {"inst": "failure"}

        self.assertEqual("inst", factory.CreateInstance())
        mock_ssh.Ssh.assert_called_once()
        mock_client_obj.InitRemoteHost.assert_called_once()
        mock_cvd_utils.UploadImageZip.assert_not_called()
        mock_cvd_utils.UploadImageDir.assert_called_with(
            mock.ANY, "/mock/img")
        mock_cvd_utils.UploadCvdHostPackage.assert_called_with(
            mock.ANY, "/mock/cvd.tar.gz")
        mock_client_obj.LaunchCvd.assert_called_with(
            "inst",
            mock_avd_spec,
            mock_avd_spec.cfg.extra_data_disk_size_gb,
            boot_timeout_secs=mock_avd_spec.boot_timeout_secs)
        self.assertEqual({"inst": "failure"}, factory.GetFailures())

    @mock.patch("acloud.public.actions.remote_host_cf_device_factory."
                "cvd_compute_client_multi_stage")
    @mock.patch("acloud.public.actions.remote_host_cf_device_factory.ssh")
    @mock.patch("acloud.public.actions.remote_host_cf_device_factory."
                "cvd_utils")
    def testCreateInstanceWithImageZip(self, mock_cvd_utils, mock_ssh,
                                       _mock_client):
        """Test CreateInstance with local image zip."""
        mock_avd_spec = self._CreateMockAvdSpec()
        mock_avd_spec.image_source = constants.IMAGE_SRC_LOCAL
        factory = remote_host_cf_device_factory.RemoteHostDeviceFactory(
            mock_avd_spec, local_image_artifact="/mock/img.zip",
            cvd_host_package_artifact="/mock/cvd.tar.gz")

        mock_client_obj = factory.GetComputeClient()
        mock_client_obj.FormatRemoteHostInstanceName.return_value = "inst"
        mock_client_obj.LaunchCvd.return_value = {}

        self.assertEqual("inst", factory.CreateInstance())
        mock_ssh.Ssh.assert_called_once()
        mock_client_obj.InitRemoteHost.assert_called_once()
        mock_cvd_utils.UploadImageZip.assert_called_with(
            mock.ANY, "/mock/img.zip")
        mock_cvd_utils.UploadImageDir.assert_not_called()
        mock_cvd_utils.UploadCvdHostPackage.assert_called_with(
            mock.ANY,"/mock/cvd.tar.gz")
        mock_client_obj.LaunchCvd.assert_called()
        self.assertFalse(factory.GetFailures())

    @mock.patch("acloud.public.actions.remote_host_cf_device_factory."
                "cvd_compute_client_multi_stage")
    @mock.patch("acloud.public.actions.remote_host_cf_device_factory.ssh")
    @mock.patch("acloud.public.actions.remote_host_cf_device_factory."
                "subprocess.check_call")
    @mock.patch("acloud.public.actions.remote_host_cf_device_factory.glob")
    def testCreateInstanceWithRemoteImages(self, mock_glob, mock_check_call,
                                           mock_ssh, _mock_client):
        """Test CreateInstance with remote images."""
        mock_avd_spec = self._CreateMockAvdSpec()
        mock_avd_spec.image_source = constants.IMAGE_SRC_REMOTE
        mock_ssh_obj = mock.Mock()
        mock_ssh.Ssh.return_value = mock_ssh_obj
        mock_ssh_obj.GetBaseCmd.return_value = "/mock/ssh"
        mock_glob.glob.return_value = ["/mock/super.img"]
        factory = remote_host_cf_device_factory.RemoteHostDeviceFactory(
            mock_avd_spec)

        mock_client_obj = factory.GetComputeClient()
        mock_client_obj.FormatRemoteHostInstanceName.return_value = "inst"
        mock_client_obj.LaunchCvd.return_value = {}

        self.assertEqual("inst", factory.CreateInstance())
        mock_ssh.Ssh.assert_called_once()
        mock_client_obj.InitRemoteHost.assert_called_once()
        mock_check_call.assert_called_once()
        mock_ssh.ShellCmdWithRetry.assert_called_once()
        self.assertRegex(mock_ssh.ShellCmdWithRetry.call_args[0][0],
                         r"^tar -cf - --lzop -S -C \S+ super\.img \| "
                         r"/mock/ssh -- tar -xf - --lzop -S$")
        mock_client_obj.LaunchCvd.assert_called()
        self.assertFalse(factory.GetFailures())


if __name__ == "__main__":
    unittest.main()
