Name:           python3-impera
Version:        0.3

Release:        1%{?dist}
Summary:        Impera configuration management tool

Group:          Development/Languages
License:        LGPLv2+
URL:            http://impera.io
Source0:        https://github.com/bartv/impera/archive/%{version}.tar.gz#/impera-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
BuildRequires:  systemd

Requires:       python3
Requires:       python3-amqp
Requires:       python3-tornado
Requires:       python3-dateutil
Requires:       python3-execnet
Requires:       python3-colorlog
Requires:       python3-blitzdb
Requires:       python3-antlr3
Requires:       python3-PyYAML
Requires:       python-virtualenv
Requires:       python3-urllib3
Requires:       python3-pymongo
Requires:       git
Requires(pre):  shadow-utils

Obsoletes:      python3-imp <= 0.50

%package server
Summary:        The configuration and service files to start the Impera server
Requires:       python3-impera
Obsoletes:      python3-imp-server <= 0.50

%package agent
Summary:        The configuration and service files to start the Impera agent
Requires:       python3-impera
Obsoletes:      python3-imp-agent <= 0.50

%description

%description server

%description agent

%prep
%setup -q -n impera-%{version}

%build
%{__python3} setup.py build


%install
rm -rf %{buildroot}
%{__python3} setup.py install -O1 --skip-build --root %{buildroot}
chmod -x LICENSE
mkdir -p %{buildroot}%{_localstatedir}/lib/impera
mkdir -p %{buildroot}/etc/impera
install -p -m 644 misc/impera.cfg %{buildroot}/etc/impera.cfg

mkdir -p %{buildroot}%{_unitdir}
install -p -m 644 misc/impera-agent.service $RPM_BUILD_ROOT%{_unitdir}/impera-agent.service
install -p -m 644 misc/impera-server.service $RPM_BUILD_ROOT%{_unitdir}/impera-server.service

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
%doc LICENSE docs/*
%{python3_sitelib}/impera-%{version}-py?.?.egg-info
%{python3_sitelib}/impera
%{_bindir}/impera
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
* Thu Jan 08 2015 Bart Vanbrabant <bart@impera.io> - 0.1
- Initial release

