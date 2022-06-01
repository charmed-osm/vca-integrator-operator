<!-- Copyright 2022 Canonical Ltd.
See LICENSE file for licensing details. -->

# OSM VCA Integrator Operator

[![code style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black/tree/main)
[![Run-Tests](https://github.com/charmed-osm/vca-integrator-operator/actions/workflows/ci.yaml/badge.svg)](https://github.com/charmed-osm/vca-integrator-operator/actions/workflows/ci.yaml)

[![VCA Integrator](https://charmhub.io/vca-integrator/badge.svg)](https://charmhub.io/vca-integrator)

## Description

TODO

## How-to guides

### Deploy and configure

Deploy the OSM VCA Integrator Charm using the Juju command line:

```shell
$ juju add-model osm-vca-integrator
$ juju deploy osm-vca-integrator
$ juju config osm-vca-integrator \
    k8s-cloud=microk8s \
    controllers="`cat ~/.local/share/juju/controllers.yaml`" \
    accounts="`cat ~/.local/share/juju/accounts.yaml`" \
    public-key="`cat ~/.local/share/juju/ssh/juju_id_rsa.pub`"
```

### Relate with VCA Integrator

If you are developing a charm that needs to integrate with VCA Integrator, please follow [the instructions](https://charmhub.io/vca-integrator/libraries/vca-integrator) to do so.


## Contributing

Please see the [Juju SDK docs](https://juju.is/docs/sdk) for guidelines
on enhancements to this charm following best practice guidelines, and
`CONTRIBUTING.md` for developer guidance.
