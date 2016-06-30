# Use release 0 for prerelease version.
%define release 0.rc3
%define version 2016.3

%define sourceversion %{version}%{?buildid}

%{?scl:%scl_package python-colorlog}
%{!?scl:%global pkg_name %{name}}

Name:           %{?scl_prefix}python%{?!scl:3}-inmanta
Version:        %{version}

Release:        %{release}%{?buildid}%{?tag}%{?dist}
Summary:        Inmanta configuration management tool

Group:          Development/Languages
License:        LGPLv2+
URL:            http://inmanta.com
Source0:        inmanta-%{sourceversion}.tar.gz
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
Requires:       %scl_require_package rh-python34 python-ruamel-yaml
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
Requires:       python3-ruamel-yaml
%endif

BuildRequires:  systemd

Requires:       git
Requires(pre):  shadow-utils
Obsoletes:      %{?scl_prefix}python%{?!scl:3}-impera

%package server
Summary:        The configuration and service files to start the Inmanta server
Requires:       %{?scl_prefix}python%{?!scl:3}-inmanta

%package agent
Summary:        The configuration and service files to start the Inmanta agent
Requires:       %{?scl_prefix}python%{?!scl:3}-inmanta

%description

%description server

%description agent

%prep
%setup -q -n inmanta-%{sourceversion}

%build
%{?scl:scl enable %{scl} "}
PYTHONPATH=src %{__python3} src/inmanta/parser/plyInmantaParser.py
%{__python3} setup.py build
%{?scl:"}

%install
rm -rf %{buildroot}
%{?scl:scl enable %{scl} "}
%{__python3} setup.py install -O1 --skip-build --root %{buildroot}
%{?scl:"}
chmod -x LICENSE
mkdir -p %{buildroot}%{_localstatedir}/lib/inmanta
mkdir -p %{buildroot}/etc/inmanta
mkdir -p %{buildroot}/var/log/inmanta
install -p -m 644 misc/inmanta.cfg %{buildroot}/etc/inmanta.cfg

mkdir -p %{buildroot}%{_unitdir}
%if 0%{?scl:1}
install -p -m 644 misc/inmanta-agent-scl.service $RPM_BUILD_ROOT%{_unitdir}/inmanta-agent.service
install -p -m 644 misc/inmanta-server-scl.service $RPM_BUILD_ROOT%{_unitdir}/inmanta-server.service
%else
install -p -m 644 misc/inmanta-agent.service $RPM_BUILD_ROOT%{_unitdir}/inmanta-agent.service
install -p -m 644 misc/inmanta-server.service $RPM_BUILD_ROOT%{_unitdir}/inmanta-server.service
%endif

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
%doc LICENSE docs/*
%{python3_sitelib}/inmanta-%{sourceversion}-py*.egg-info
%{python3_sitelib}/inmanta
%{_bindir}/inmanta
%{_bindir}/inmanta-cli
%attr(-, inmanta, inmanta) %{_localstatedir}/lib/inmanta
%config %attr(-, root, root) /etc/inmanta.cfg
%attr(-, inmanta, inmanta) /var/log/inmanta
%attr(-, root, root)/etc/inmanta

%files server
%attr(-,root,root) %{_unitdir}/inmanta-server.service

%files agent
%attr(-,root,root) %{_unitdir}/inmanta-agent.service

%post agent
%systemd_post inmanta-agent.service

%preun agent
%systemd_preun inmanta-server.service

%postun agent
%systemd_postun_with_restart inmanta-server.service

%post server
%systemd_post inmanta-agent.service

%preun server
%systemd_preun inmanta-server.service

%postun server
%systemd_postun_with_restart inmanta-server.service

%pre
getent group inmanta >/dev/null || groupadd -r inmanta
getent passwd inmanta >/dev/null || \
    useradd -r -g inmanta -d /var/lib/inmanta -s /bin/bash \
    -c "Account used by the Inmanta daemons" inmanta
exit

%changelog
* Mon May 30 2016 Bart Vanbrabant <bart.vanbrabant@inmanta.com> - 2016.3
- Rename to Inmanta

* Thu Jan 08 2015 Bart Vanbrabant <bart.vanbrabant@inmanta.com> - 0.1
- Initial release

