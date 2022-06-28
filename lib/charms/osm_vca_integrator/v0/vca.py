# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""VCA Library.

VCA stands for VNF Configuration and Abstraction, and is one of the core components
of OSM. The Juju Controller is in charged of this role.

This [library](https://juju.is/docs/sdk/libraries) implements both sides of the
`vca` [interface](https://juju.is/docs/sdk/relations).

The *provider* side of this interface is implemented by the
[osm-vca-integrator Charmed Operator](https://charmhub.io/osm-vca-integrator).

helps to integrate with the
vca-integrator charm, which provides data needed to the OSM components that need
to talk to the VCA, and

Any Charmed OSM component that *requires* to talk to the VCA should implement
the *requirer* side of this interface.

In a nutshell using this library to implement a Charmed Operator *requiring* VCA data
would look like

```
$ charmcraft fetch-lib charms.osm_vca_integrator.v0.vca
```

`metadata.yaml`:

```
requires:
  vca:
    interface: osm-vca
```

`src/charm.py`:

```
from charms.osm_vca_integrator.v0.vca import VcaData, VcaIntegratorEvents, VcaRequires
from ops.charm import CharmBase


class MyCharm(CharmBase):

    on = VcaIntegratorEvents()

    def __init__(self, *args):
        super().__init__(*args)
        self.vca = VcaRequires(self)
        self.framework.observe(
            self.on.vca_data_changed,
            self._on_vca_data_changed,
        )

    def _on_vca_data_changed(self, event):
        # Get Vca data
        data: VcaData = self.vca.data
        # data.endpoints => "localhost:17070"
```

You can file bugs
[here](https://github.com/charmed-osm/osm-vca-integrator-operator/issues)!
"""

import logging
from typing import Dict, Optional

from ops.charm import CharmBase, CharmEvents, RelationChangedEvent
from ops.framework import EventBase, EventSource, Object

# The unique Charmhub library identifier, never change it
from ops.model import Relation

# The unique Charmhub library identifier, never change it
LIBID = "746b36c382984e5c8660b78192d84ef9"

# Increment this major API version when introducing breaking changes
LIBAPI = 0

# Increment this PATCH version before using `charmcraft publish-lib` or reset
# to 0 if you are raising the major API version
LIBPATCH = 2


logger = logging.getLogger(__name__)


class VcaDataChangedEvent(EventBase):
    """Event emitted whenever there is a change in the vca data."""

    def __init__(self, handle):
        super().__init__(handle)


class VcaIntegratorEvents(CharmEvents):
    """VCA Integrator events.

    This class defines the events that ZooKeeper can emit.

    Events:
        vca_data_changed (_VcaDataChanged)
    """

    vca_data_changed = EventSource(VcaDataChangedEvent)


RELATION_MANDATORY_KEYS = ("endpoints", "user", "secret", "public-key", "cacert")
RELATION_OPTIONAL_KEYS = ("lxd-cloud", "k8s-cloud")


class VcaData:
    """Vca data class."""

    def __init__(self, data: Dict[str, str]) -> None:
        self.data = data
        self.endpoints = data["endpoints"]
        self.user = data["user"]
        self.secret = data["secret"]
        self.public_key = data["public-key"]
        self.cacert = data["cacert"]
        self.lxd_cloud = data.get("lxd-cloud")
        self.lxd_credentials = data.get("lxd-credentials")
        self.k8s_cloud = data.get("k8s-cloud")
        self.k8s_credentials = data.get("k8s-credentials")


class VcaDataMissingError(Exception):
    """Data missing exception."""


class VcaRequires(Object):
    """Requires part of the vca relation.

    Attributes:
        endpoint_name: Endpoint name of the charm for the vca relation.
        data: Vca data from the relation.
    """

    def __init__(self, charm: CharmBase, endpoint_name: str = "vca") -> None:
        super().__init__(charm, endpoint_name)
        self._charm = charm
        self.endpoint_name = endpoint_name
        self.framework.observe(charm.on[endpoint_name].relation_changed, self._on_relation_changed)

    @property
    def data(self) -> Optional[VcaData]:
        """Vca data from the relation."""
        relation: Relation = self.model.get_relation(self.endpoint_name)
        if not relation or relation.app not in relation.data:
            logger.debug("no application data in the event")
            return

        relation_data = relation.data[relation.app]
        try:
            self._validate_relation_data(relation_data)
            return VcaData(relation_data)
        except VcaDataMissingError as e:
            logger.warning(e)

    def _on_relation_changed(self, event: RelationChangedEvent) -> None:
        if event.app not in event.relation.data:
            logger.debug("no application data in the event")
            return

        relation_data = event.relation.data[event.app]
        try:
            self._validate_relation_data(relation_data)
            self._charm.on.vca_data_changed.emit()
        except VcaDataMissingError as e:
            logger.warning(e)

    def _validate_relation_data(self, relation_data: Dict[str, str]) -> None:
        if not all(required_key in relation_data for required_key in RELATION_MANDATORY_KEYS):
            raise VcaDataMissingError("vca data not ready yet")

        clouds = ("lxd-cloud", "k8s-cloud")
        if not any(cloud in relation_data for cloud in clouds):
            raise VcaDataMissingError("no clouds defined yet")


class VcaProvides(Object):
    """Provides part of the vca relation.

    Attributes:
        endpoint_name: Endpoint name of the charm for the vca relation.
    """

    def __init__(self, charm: CharmBase, endpoint_name: str = "vca") -> None:
        super().__init__(charm, endpoint_name)
        self.endpoint_name = endpoint_name

    def update_vca_data(self, vca_data: VcaData) -> None:
        """Update vca data in relation.

        Args:
            vca_data: VcaData object.
        """
        relation: Relation
        for relation in self.model.relations[self.endpoint_name]:
            if not relation or self.model.app not in relation.data:
                logger.debug("relation app data not ready yet")
            for key, value in vca_data.data.items():
                relation.data[self.model.app][key] = value
