# Use release 0 for prerelease version.
%define release 1
%define version 2016.2.3

%define sourceversion %{version}%{?buildid}

%{?scl:%scl_package python-colorlog}
%{!?scl:%global pkg_name %{name}}

Name:           %{?scl_prefix}python%{?!scl:3}-impera
Version:        %{version}

Release:        %{release}%{?buildid}%{?tag}%{?dist}
Summary:        Impera configuration management tool

Group:          Development/Languages
License:        LGPLv2+
URL:            http://impera.io
Source0:        https://github.com/impera-io/impera/archive/%{sourceversion}.tar.gz#/impera-%{sourceversion}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildArch:      noarch
%{?scl:Requires: %scl_runtime}

%if 0%{?scl:1}
BuildRequires:  scl-utils-build
BuildRequires:  %scl_require_package rh-python34 python-devel
BuildRequires:  %scl_require_package rh-python34 python-setuptools
BuildRequires:  %scl_require_package rh-python34 python-ply

Requires:       %scl_require_package rh-python34 runtime
Requires:       %scl_require_package rh-python34 python-tornado
Requires:       %scl_require_package rh-python34 python-dateutil
Requires:       %scl_require_package rh-python34 python-execnet
Requires:       %scl_require_package rh-python34 python-colorlog
Requires:       %scl_require_package rh-python34 python-ply
Requires:       %scl_require_package rh-python34 python-PyYAML
Requires:       %scl_require_package rh-python34 python-virtualenv
Requires:       %scl_require_package rh-python34 python-pymongo
Requires:       %scl_require_package rh-python34 python-motorengine
%else
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
BuildRequires:  python3-ply

Requires:       python3
Requires:       python3-tornado
Requires:       python3-dateutil
Requires:       python3-execnet
Requires:       python3-colorlog
Requires:       python3-ply
Requires:       python3-PyYAML
Requires:       python-virtualenv
Requires:       python3-pymongo
Requires:       python3-motorengine
Requires:       python3-devel
Requires:       python3-cliff
%endif

BuildRequires:  systemd

Requires:       git
Requires(pre):  shadow-utils

%package server
Summary:        The configuration and service files to start the Impera server
Requires:       %{?scl_prefix}python3-impera

%package agent
Summary:        The configuration and service files to start the Impera agent
Requires:       %{?scl_prefix}python3-impera

%description

%description server

%description agent

%prep
%setup -q -n impera-%{sourceversion}

%build
%{?scl:scl enable %{scl} "}
PYTHONPATH=src %{__python3} src/impera/parser/plyInmantaParser.py
%{__python3} setup.py build
%{?scl:"}

%install
rm -rf %{buildroot}
%{?scl:scl enable %{scl} "}
%{__python3} setup.py install -O1 --skip-build --root %{buildroot}
%{?scl:"}
chmod -x LICENSE
mkdir -p %{buildroot}%{_localstatedir}/lib/impera
mkdir -p %{buildroot}/etc/impera
install -p -m 644 misc/impera.cfg %{buildroot}/etc/impera.cfg

mkdir -p %{buildroot}%{_unitdir}
%if 0%{?scl:1}
install -p -m 644 misc/impera-agent-scl.service $RPM_BUILD_ROOT%{_unitdir}/impera-agent.service
install -p -m 644 misc/impera-server-scl.service $RPM_BUILD_ROOT%{_unitdir}/impera-server.service
%else
install -p -m 644 misc/impera-agent.service $RPM_BUILD_ROOT%{_unitdir}/impera-agent.service
install -p -m 644 misc/impera-server.service $RPM_BUILD_ROOT%{_unitdir}/impera-server.service
%endif

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
%doc LICENSE docs/*
%{python3_sitelib}/impera-%{sourceversion}-py*.egg-info
%{python3_sitelib}/impera
%{_bindir}/impera
%{_bindir}/impera-cli
%attr(-, impera, impera) %{_localstatedir}/lib/impera
%config %attr(-, root, root) /etc/impera.cfg
%attr(-, root, root)/etc/impera

%files server
%attr(-,root,root) %{_unitdir}/impera-server.service

%files agent
%attr(-,root,root) %{_unitdir}/impera-agent.service

%post agent
%systemd_post impera-agent.service

%preun agent
%systemd_preun impera-server.service

%postun agent
%systemd_postun_with_restart impera-server.service

%post server
%systemd_post impera-agent.service

%preun server
%systemd_preun impera-server.service

%postun server
%systemd_postun_with_restart impera-server.service

%pre
getent group impera >/dev/null || groupadd -r impera
getent passwd impera >/dev/null || \
    useradd -r -g impera -d /var/lib/impera -s /bin/bash \
    -c "Account used by the Impera daemons" impera
exit

%changelog
* Wed May 04 2016 Bart Vanbrabant <bart.vanbrabant@inmanta.com> - 2016.2.1
- New bugfix release
* Thu Jan 08 2015 Bart Vanbrabant <bart@impera.io> - 0.1
- Initial release

