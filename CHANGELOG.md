# Changelog

All notable changes to PyHSS are documented in this file, beginning from [Service Overhaul #168](https://github.com/nickvsnetworking/pyhss/pull/168).

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.2] - 2024-07-03

### Added

- Configurable DWRs sendable to connected peers.
- Configurable outbound roaming rules on a per-network and per-subscriber basis.
- /pcrf/clr_subscriber for ease of use.
- Support for OCS webhook notifications on CCR-I and CCR-T.

### Fixed

- Removed '+' from MSISDNs when storing in the database.
- CCR-based logical bug when emergency attach procedure is performed.
- Repeated ECRs leaking open SQL sessions.
- Forced string evaluation for tacDatabasePath.

## [1.0.1] - 2024-01-23


### Removed
 - Assert on missing "IMS Services" for AAA/Audio Request

### Changed

- Reduced verbosity of failing subscriber lookups to debug
- Added CORS headers: [Zarya/171](https://github.com/nickvsnetworking/pyhss/pull/171)
- Gx RAR now dynamically creates TFT up to 512k based on UE request.
- SQN Resync now propogates via Geored when enabled 
- Renamed sh_profile to xcap_profile in ims_subscriber
- Rebuilt keys using unique namespace for redis-sentinel / stateless compatibility.

### Fixed

- Geored failing when multiple peers defined and socket closes.
- Error in Update_Serving_MME when supplied with a NoneType timestamp.

### Added

- Support for CLR-based PCSCF restoration via `/pcrf/pcscf_restoration` and `/pcrf/pcscf_restoration_subscriber` in API.
- Optional immediateReattach parameter in Request_16777251_317, via CLR-Flags
- Sh-IMS-Data and IMSPrivateUserIdentity to default_sh_user_data.xml
- Optional config parameter `api.enable_insecure_auc` to allow retrieval of AuC keys through API
- sh_template_path in ims_subscriber
- generateUpgade.sh for generating alembic upgrade scripts
- Control of outbound roaming S6a AIR and ULA responses through roaming_rule and roaming_network objects.
- Roaming management on a per-subscriber basis, through subscriber.roaming_enabled and subscriber.roaming_rule_list.
- Support for Gx and Rx auth of unknown subscribers attaching via SOS.
- Preliminary support for SCTP.
- Additional prometheus metrics.

## [1.0.0] - 2023-09-27

### Added

 - Systemd service files for PyHSS services
 - /oam/diameter_peers endpoint
 - /oam/deregister/{imsi} endpoint
 - /geored/peers endpoint
 - /geored/webhooks endpoint
 - Dependency on Redis 7 for inter-service messaging
 - Significant performance improvements under load
 - Basic Rx support for RAA, AAA, ASA and STA
 - Rx MO call flow support (AAR -> RAR -> RAA -> AAA)
 - Dedicated bearer setup and teardown on Rx call
 - Asymmetric geored support
 - Configurable redis connection (Unix socket or TCP)
 - Basic database upgrade support in tools/databaseUpgrade
 - PCSCF state storage in ims_subscriber
 - (Experimental) Working horizontal scalability

### Changed

- Split logical functions of PyHSS into 6 service processes
- Logtool no longer handles metric processing
- Updated config.yaml
- Gx CCR-T now flushes PGW / IMS data, depending on Called-Station-Id
- Benchmarked capability of at least ~500 diameter requests per second with a response time of under 2 seconds on a local network.

### Fixed

 - Memory leaking in diameter.py
 - Gx CCA now supports apn inside a plmn based uri
 - AVP_Preemption_Capability and AVP_Preemption_Vulnerability now presents correctly in all diameter messages
 - Crash when webhook or geored endpoints enabled and no peers defined
 - CPU overutilization on all services

### Removed

- Multithreading in all services, except for metricService

[1.0.0]: https://github.com/nickvsnetworking/pyhss/releases/tag/1.0.0
[1.0.1]: https://github.com/nickvsnetworking/pyhss/releases/tag/1.0.1
[1.0.2]: https://github.com/nickvsnetworking/pyhss/releases/tag/1.0.2