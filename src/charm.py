#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""VcaIntegrator K8s charm module."""

import asyncio
import base64
import logging
import os
from pathlib import Path
from typing import Dict, Set

import yaml
from charms.osm_vca_integrator.v0.vca import VcaData, VcaProvides
from juju.controller import Controller
from ops.charm import CharmBase
from ops.main import main
from ops.model import ActiveStatus, BlockedStatus, StatusBase

logger = logging.getLogger(__name__)

GO_COOKIES = "/root/.go-cookies"
JUJU_DATA = os.environ["JUJU_DATA"] = "/root/.local/share/juju"
JUJU_CONFIGS = {
    "public-key": "ssh/juju_id_rsa.pub",
    "controllers": "controllers.yaml",
    "accounts": "accounts.yaml",
}


class CharmError(Exception):
    """Charm Error Exception."""

    def __init__(self, message: str, status_class: StatusBase = BlockedStatus) -> None:
        self.message = message
        self.status_class = status_class
        self.status = status_class(message)


class VcaIntegratorCharm(CharmBase):
    """VcaIntegrator K8s Charm operator."""

    def __init__(self, *args):
        super().__init__(*args)
        self.vca_provider = VcaProvides(self)
        # Observe charm events
        event_observe_mapping = {
            self.on.config_changed: self._on_config_changed,
            self.on.vca_relation_joined: self._on_config_changed,
        }
        for event, observer in event_observe_mapping.items():
            self.framework.observe(event, observer)

    # ---------------------------------------------------------------------------
    #   Properties
    # ---------------------------------------------------------------------------

    @property
    def clouds_set(self) -> Set:
        """Clouds set in the configuration."""
        clouds_set = set()
        for cloud_config in ["k8s-cloud", "lxd-cloud"]:
            if cloud_name := self.config.get(cloud_config):
                clouds_set.add(cloud_name.split(":")[0])
        return clouds_set

    @property
    def vca_data(self) -> VcaData:
        """Get VCA data."""
        return VcaData(self._get_vca_data())

    # ---------------------------------------------------------------------------
    #   Handlers for Charm Events
    # ---------------------------------------------------------------------------

    def _on_config_changed(self, _) -> None:
        """Handler for the config-changed event."""
        # Validate charm configuration
        try:
            self._validate_config()
            self._write_controller_config_files()
            self._check_controller()
            self.vca_provider.update_vca_data(self.vca_data)
            self.unit.status = ActiveStatus()
        except CharmError as e:
            self.unit.status = e.status

    # ---------------------------------------------------------------------------
    #   Validation and configuration
    # ---------------------------------------------------------------------------

    def _validate_config(self) -> None:
        """Validate charm configuration.

        Raises:
            Exception: if charm configuration is invalid.
        """
        # Check mandatory fields
        for mandatory_field in [
            "controllers",
            "accounts",
            "public-key",
        ]:
            if not self.config.get(mandatory_field):
                raise CharmError(f'missing config: "{mandatory_field}"')
        # Check if any clouds are set
        if not self.clouds_set:
            raise CharmError("no clouds set")

        if self.config.get("model-configs"):
            try:
                yaml.safe_load(self.config["model-configs"])
            except Exception:
                raise CharmError("invalid yaml format for model-configs")

    def _write_controller_config_files(self) -> None:
        Path(f"{JUJU_DATA}/ssh").mkdir(parents=True, exist_ok=True)
        go_cookies = Path(GO_COOKIES)
        if not go_cookies.is_file():
            go_cookies.write_text(data="[]")
        for config, path in JUJU_CONFIGS.items():
            Path(f"{JUJU_DATA}/{path}").expanduser().write_text(self.config[config])

    def _check_controller(self):
        loop = asyncio.get_event_loop()
        # Check controller connectivity
        loop.run_until_complete(self._check_controller_connectivity())
        # Check clouds exist in controller
        loop.run_until_complete(self._check_clouds_in_controller())

    async def _check_controller_connectivity(self):
        controller = Controller()
        await controller.connect()
        await controller.disconnect()

    async def _check_clouds_in_controller(self):
        controller = Controller()
        await controller.connect()
        try:
            controller_clouds = await controller.clouds()
            for cloud in self.clouds_set:
                if f"cloud-{cloud}" not in controller_clouds.clouds:
                    raise CharmError(f"Cloud {cloud} does not exist in the controller")
        finally:
            await controller.disconnect()

    def _get_vca_data(self) -> Dict[str, str]:
        loop = asyncio.get_event_loop()
        data_from_config = self._get_vca_data_from_config()
        coro_data_from_controller = loop.run_until_complete(self._get_vca_data_from_controller())
        vca_data = {**data_from_config, **coro_data_from_controller}
        logger.debug(f"vca data={vca_data}")
        return vca_data

    def _get_vca_data_from_config(self) -> Dict[str, str]:
        data = {"public-key": self.config["public-key"]}
        if self.config.get("lxd-cloud"):
            lxd_cloud_parts = self.config["lxd-cloud"].split(":")
            data.update(
                {
                    "lxd-cloud": lxd_cloud_parts[0],
                    "lxd-credentials": lxd_cloud_parts[1]
                    if len(lxd_cloud_parts) > 1
                    else lxd_cloud_parts[0],
                }
            )
        if self.config.get("k8s-cloud"):
            k8s_cloud_parts = self.config["k8s-cloud"].split(":")
            data.update(
                {
                    "k8s-cloud": k8s_cloud_parts[0],
                    "k8s-credentials": k8s_cloud_parts[1]
                    if len(k8s_cloud_parts) > 1
                    else k8s_cloud_parts[0],
                }
            )
        if self.config.get("model-configs"):
            data["model-configs"] = yaml.safe_load(self.config["model-configs"])

        return data

    async def _get_vca_data_from_controller(self) -> Dict[str, str]:
        controller = Controller()
        await controller.connect()
        try:
            connection = controller._connector._connection
            return {
                "endpoints": ",".join(await controller.api_endpoints),
                "user": connection.username,
                "secret": connection.password,
                "cacert": base64.b64encode(connection.cacert.encode("utf-8")).decode("utf-8"),
            }
        finally:
            await controller.disconnect()


if __name__ == "__main__":  # pragma: no cover
    main(VcaIntegratorCharm)
