# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from threading import Lock

from sqlalchemy import Column, String, BigInteger, TIMESTAMP, create_engine, MetaData, Sequence, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker,relationship


Base = declarative_base()


class OeCompatibilityOverallUnit(Base):
    __tablename__ = 'oe_compatibility_overall_unit'
    __table_args__ = {'comment': 'openEuler支持的整机信息表，存储了openEuler支持的整机的架构、CPU型号、硬件厂家、硬件型号和相关的openEuler版本'}
    id = Column(BigInteger, primary_key=True)
    architecture = Column(String(), comment='openEuler支持的整机信息的架构')
    bios_uefi = Column(String())
    certification_addr = Column(String())
    certification_time = Column(String())
    commitid = Column(String())
    computer_type = Column(String())
    cpu = Column(String(), comment='openEuler支持的整机信息的CPU型号')
    date = Column(String())
    friendly_link = Column(String())
    hard_disk_drive = Column(String())
    hardware_factory = Column(String(), comment='openEuler支持的整机信息的硬件厂家')
    hardware_model = Column(String(), comment='openEuler支持的整机信息的硬件型号')
    host_bus_adapter = Column(String())
    lang = Column(String())
    main_board_bodel = Column(String())
    openeuler_version = Column(String(), comment='openEuler支持的整机信息的相关的openEuler版本')
    ports_bus_types = Column(String())
    product_information = Column(String())
    ram = Column(String())
    update_time = Column(String())
    video_adapter = Column(String())
    compatibility_configuration = Column(String())
    boardCards = Column(String())


class OeCompatibilityCard(Base):
    __tablename__ = 'oe_compatibility_card'
    __table_args__ = {'comment': 'openEuler支持的板卡信息表，存储了openEuler支持的板卡信息的支持架构、板卡型号、芯片信号、芯片厂家、驱动名称、相关的openEuler版本、类型和版本'}
    id = Column(BigInteger, primary_key=True)
    architecture = Column(String(), comment='openEuler支持的板卡信息的支持架构')
    board_model = Column(String(), comment='openEuler支持的板卡信息的板卡型号')
    chip_model = Column(String(), comment='openEuler支持的板卡信息的芯片型号')
    chip_vendor = Column(String(), comment='openEuler支持的板卡信息的芯片厂家')
    device_id = Column(String())
    download_link = Column(String())
    driver_date = Column(String())
    driver_name = Column(String(), comment='openEuler支持的板卡信息的驱动名称')
    driver_size = Column(String())
    item = Column(String())
    lang = Column(String())
    openeuler_version = Column(String(), comment='openEuler支持的板卡信息的相关的openEuler版本')
    sha256 = Column(String())
    ss_id = Column(String())
    sv_id = Column(String())
    type = Column(String(), comment='openEuler支持的板卡信息的类型')
    vendor_id = Column(String())
    version = Column(String(), comment='openEuler支持的板卡信息的版本')


class OeCompatibilityOpenSourceSoftware(Base):
    __tablename__ = 'oe_compatibility_open_source_software'
    __table_args__ = {'comment': 'openEuler支持的开源软件信息表，存储了openEuler支持的开源软件的相关openEuler版本、支持的架构、软件属性、开源协议、软件类型、软件名称和软件版本'}
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    openeuler_version = Column(String(), comment='openEuler支持的开源软件信息表的相关openEuler版本')
    arch = Column(String(), comment='openEuler支持的开源软件信息的支持的架构')
    property = Column(String(), comment='openEuler支持的开源软件信息的软件属性')
    result_url = Column(String())
    result_root = Column(String())
    bin = Column(String())
    uninstall = Column(String())
    license = Column(String(), comment='openEuler支持的开源软件信息的开源协议')
    libs = Column(String())
    install = Column(String())
    src_location = Column(String())
    group = Column(String())
    cmds = Column(String())
    type = Column(String(), comment='openEuler支持的开源软件信息的软件类型')
    softwareName = Column(String())
    category = Column(String(), comment='openEuler支持的开源软件信息的软件名称')
    version = Column(String(), comment='openEuler支持的开源软件信息的软件版本')
    downloadLink = Column(String())


class OeCompatibilityCommercialSoftware(Base):
    __tablename__ = 'oe_compatibility_commercial_software'
    __table_args__ = {'comment': 'openEuler支持的商业软件信息表，存储了openEuler支持的商业软件的软件类型、测试机构、软件名称、厂家名称和相关的openEuler版本'}
    id = Column(BigInteger, primary_key=True,)
    data_id = Column(String())
    type = Column(String(), comment='openEuler支持的商业软件的软件类型')
    test_organization = Column(String(), comment='openEuler支持的商业软件的测试机构')
    product_name = Column(String(), comment='openEuler支持的商业软件的软件名称')
    product_version = Column(String(), comment='openEuler支持的商业软件的软件版本')
    company_name = Column(String(), comment='openEuler支持的商业软件的厂家名称')
    platform_type_and_server_model = Column(String())
    authenticate_link = Column(String())
    openeuler_version = Column(String(), comment='openEuler支持的商业软件的openEuler版本')
    region = Column(String())


class OeCompatibilityOepkgs(Base):
    __tablename__ = 'oe_compatibility_oepkgs'
    __table_args__ = {
        'comment': 'openEuler支持的软件包信息表，存储了openEuler支持软件包的名称、简介、是否为官方版本标识、相关的openEuler版本、rpm包下载链接、源码包下载链接、支持的架构、版本'}
    id = Column(String(), primary_key=True)
    name = Column(String(), comment='openEuler支持的软件包的版本')
    summary = Column(String(), comment='openEuler支持的软件包的简介')
    repotype = Column(String(), comment='openEuler支持的软件包的是否为官方版本标识')
    openeuler_version = Column(String(), comment='openEuler支持的软件包的相关的openEuler版本')
    rpmpackurl = Column(String(), comment='openEuler支持的软件包的rpm包下载链接')
    srcrpmpackurl = Column(String(), comment='openEuler支持的软件包的源码包下载链接')
    arch = Column(String(), comment='openEuler支持的软件包的支持的架构')
    rpmlicense = Column(String())
    version = Column(String(), comment='openEuler支持的软件包的版本')


class OeCompatibilitySolution(Base):
    __tablename__ = 'oe_compatibility_solution'
    __table_args__ = {'comment': 'openeuler支持的解决方案表，存储了openeuler支持的解决方案的架构、硬件类别、cpu型号、相关的openEuler版本、硬件型号、厂家和解决方案类型'}
    id = Column(String(), primary_key=True,)
    architecture = Column(String(), comment='openeuler支持的解决方案的架构')
    bios_uefi = Column(String())
    certification_type = Column(String(), comment='openeuler支持的解决方案的硬件')
    cpu = Column(String(), comment='openeuler支持的解决方案的硬件的cpu型号')
    date = Column(String())
    driver = Column(String())
    hard_disk_drive = Column(String())
    introduce_link = Column(String())
    lang = Column(String())
    libvirt_version = Column(String())
    network_card = Column(String())
    openeuler_version = Column(String(), comment='openeuler支持的解决方案的相关openEuler版本')
    ovs_version = Column(String())
    product = Column(String(), comment='openeuler支持的解决方案的硬件型号')
    qemu_version = Column(String())
    raid = Column(String())
    ram = Column(String())
    server_model = Column(String(), comment='openeuler支持的解决方案的厂家')
    server_vendor = Column(String())
    solution = Column(String(), comment='openeuler支持的解决方案的解决方案类型')
    stratovirt_version = Column(String())


class OeCompatibilityOsv(Base):
    __tablename__ = 'oe_compatibility_osv'
    __table_args__ = {
        'comment': 'openEuler相关的OSV(Operating System Vendor,操作系统供应商)信息表，存储了openEuler相关的OSV(Operating System Vendor,操作系统供应商)的支持的架构、版本、名称、下载链接、详细信息的链接和相关的openEuler版本'}
    id = Column(String(), primary_key=True,)
    arch = Column(String())
    os_version = Column(String(), comment='openEuler相关的OSV(Operating System Vendor,操作系统供应商)的版本')
    osv_name = Column(String(), comment='openEuler相关的OSV(Operating System Vendor,操作系统供应商)的名称')
    date = Column(String())
    os_download_link = Column(String(), comment='openEuler相关的OSV(Operating System Vendor,操作系统供应商)的下载链接')
    type = Column(String())
    details = Column(String(), comment='openEuler相关的OSV(Operating System Vendor,操作系统供应商)的详细信息的链接')
    friendly_link = Column(String())
    total_result = Column(String())
    checksum = Column(String())
    openeuler_version = Column(String(), comment='openEuler相关的OSV(Operating System Vendor,操作系统供应商)的相关的openEuler版本')


class OeCompatibilitySecurityNotice(Base):
    __tablename__ = 'oe_compatibility_security_notice'
    __table_args__ = {'comment': 'openEuler社区组安全公告信息表，存储了安全公告影响的openEuler版本、关联的cve漏洞的id、编号和详细信息的链接'}
    id = Column(String(), primary_key=True,)
    affected_component = Column(String())
    openeuler_version = Column(String(), comment='openEuler社区组安全公告信息影响的openEuler版本')
    announcement_time = Column(String())
    cve_id = Column(String(), comment='openEuler社区组安全公告关联的cve漏洞的id')
    description = Column(String())
    introduction = Column(String())
    package_name = Column(String())
    reference_documents = Column(String())
    revision_history = Column(String())
    security_notice_no = Column(String(), comment='openEuler社区组安全公告的编号')
    subject = Column(String())
    summary = Column(String())
    type = Column(String())
    notice_type = Column(String())
    cvrf = Column(String())
    package_helper_list = Column(String())
    package_hotpatch_list = Column(String())
    package_list = Column(String())
    reference_list = Column(String())
    cve_list = Column(String())
    details = Column(String(), comment='openEuler社区组安全公告的详细信息的链接')


class OeCompatibilityCveDatabase(Base):
    __tablename__ = 'oe_compatibility_cve_database'
    __table_args__ = {'comment': 'openEuler社区组cve漏洞信息表，存储了cve漏洞的公告时间、id、关联的软件包名称、简介、cvss评分'}

    id = Column(String(), primary_key=True,)
    affected_product = Column(String())
    announcement_time = Column(String(), comment='openEuler社区组cve漏洞的公告时间')
    attack_complexity_nvd = Column(String())
    attack_complexity_oe = Column(String())
    attack_vector_nvd = Column(String())
    attack_vector_oe = Column(String())
    availability_nvd = Column(String())
    availability_oe = Column(String())
    confidentiality_nvd = Column(String())
    confidentiality_oe = Column(String())
    cve_id = Column(String(), comment='openEuler社区组cve漏洞的id')
    cvsss_core_nvd = Column(String(), comment='openEuler社区组cve漏洞的cvss评分')
    cvsss_core_oe = Column(String())
    integrity_nvd = Column(String())
    integrity_oe = Column(String())
    national_cyberAwareness_system = Column(String())
    package_name = Column(String(), comment='openEuler社区组cve漏洞的关联的软件包名称')
    privileges_required_nvd = Column(String())
    privileges_required_oe = Column(String())
    scope_nvd = Column(String())
    scope_oe = Column(String())
    status = Column(String())
    summary = Column(String(), comment='openEuler社区组cve漏洞的简介')
    type = Column(String())
    user_interaction_nvd = Column(String())
    user_interactio_oe = Column(String())
    update_time = Column(TIMESTAMP())
    create_time = Column(TIMESTAMP())
    security_notice_no = Column(String())
    parser_bean = Column(String())
    cvrf = Column(String())
    package_list = Column(String())
    details = Column(String())


class OeOpeneulerSigGroup(Base):
    __tablename__ = 'oe_openeuler_sig_groups'
    __table_args__ = {'comment': 'openEuler社区特别兴趣小组信息表，存储了SIG的名称、描述等信息'}

    id = Column(BigInteger(), Sequence('sig_group_id'), primary_key=True)
    sig_name = Column(String(), comment='SIG的名称')
    description = Column(String(), comment='SIG的描述')
    created_at = Column(TIMESTAMP())
    is_sig_original = Column(String(), comment='是否为原始SIG')
    mailing_list = Column(String(), comment='SIG的邮件列表')
    repos_group = relationship("OeSigGroupRepo", back_populates="group")
    members_group = relationship("OeSigGroupMember", back_populates="group")

class OeOpeneulerSigMembers(Base):
    __tablename__ = 'oe_openeuler_sig_members'
    __table_args = { 'comment': 'openEuler社区特别兴趣小组成员信息表，储存了小组成员信息，如gitee用户名、所属组织等'}

    id = Column(BigInteger(), Sequence('sig_members_id'), primary_key=True)
    name = Column(String(), comment='成员名称')
    gitee_id = Column(String(), comment='成员gitee用户名')
    organization = Column(String(), comment='成员所属组织')
    member_role = Column(String(), comment='maintainer or committer') # repo_member
    email = Column(String(), comment='成员邮箱地址')
    # avatar_url = Column(String(), comment='成员头像地址')
    groups_member = relationship("OeSigGroupMember", back_populates="member")
    repos_member = relationship("OeSigRepoMember", back_populates="member")
    # sig_name = Column(String(), comment='成员所属SIG组')

class OeOpeneulerSigRepos(Base):
    __tablename__ = 'oe_openeuler_sig_repos'
    __table_args__ = {'comment': 'openEuler社区特别兴趣小组信息表，存储了SIG的名称、描述等信息'}

    id = Column(BigInteger(), Sequence('sig_repos_id'), primary_key=True)
    repo = Column(String(), comment='repo地址')
    url = Column(String(), comment='repo URL')
    groups_repo = relationship("OeSigGroupRepo", back_populates="repo")
    members_repo = relationship("OeSigRepoMember", back_populates="repo")
    # sig_name = Column(String(), comment='repo所属SIG组')
    # committers = Column(String(), comment='Committer成员列表')
    # maintainers = Column(String(), comment='Maintainer成员列表')

class OeSigGroupRepo(Base):
    __tablename__ = 'oe_sig_group_to_repos'
    __table_args__ = {'comment': 'SIG group id包含repos'}

    group_id = Column(BigInteger(), ForeignKey('oe_openeuler_sig_groups.id'), primary_key=True)
    repo_id = Column(BigInteger(), ForeignKey('oe_openeuler_sig_repos.id'), primary_key=True)
    member_role = Column(String(), comment='成员属性maintainer or committer')  # repo_member
    group = relationship("OeOpeneulerSigGroup", back_populates="repos_group")
    repo = relationship("OeOpeneulerSigRepos", back_populates="groups_repo")

class OeSigRepoMember(Base):
    __tablename__ = 'oe_sig_repos_to_members'
    __table_args__ = {'comment': 'SIG repo id对应维护成员'}

    member_id = Column(BigInteger(), ForeignKey('oe_openeuler_sig_members.id'), primary_key=True)
    repo_id = Column(BigInteger(), ForeignKey('oe_openeuler_sig_repos.id'), primary_key=True)

    member = relationship("OeOpeneulerSigMembers", back_populates="repos_member")
    repo = relationship("OeOpeneulerSigRepos", back_populates="members_repo")

class OeSigGroupMember(Base):
    __tablename__ = 'oe_sig_group_to_members'
    __table_args__ = {'comment': 'SIG group id对应包含成员id'}

    group_id = Column(BigInteger(), ForeignKey('oe_openeuler_sig_groups.id'), primary_key=True)
    member_id = Column(BigInteger(), ForeignKey('oe_openeuler_sig_members.id'), primary_key=True)
    group = relationship("OeOpeneulerSigGroup", back_populates="members_group")
    member = relationship("OeOpeneulerSigMembers", back_populates="groups_member")

class OeCommunityOrganizationStructure(Base):
    __tablename__ = 'oe_community_organization_structure'
    __table_args__ = {'comment': 'openEuler社区组织架构信息表，存储了openEuler社区成员所属的委员会、职位、姓名和个人信息'}
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    committee_name = Column(String(), comment='openEuler社区成员所属的委员会')
    role = Column(String(), comment='openEuler社区成员的职位')
    name = Column(String(), comment='openEuler社区成员的姓名')
    personal_message = Column(String(), comment='openEuler社区成员的个人信息')


class OeCommunityOpenEulerVersion(Base):
    __tablename__ = 'oe_community_openeuler_version'
    __table_args__ = {'comment': 'openEuler社区openEuler版本信息表，存储了openEuler版本的版本、内核版本、发布日期和版本类型'}
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    openeuler_version = Column(String(), comment='openEuler版本的版本号')
    kernel_version = Column(String(), comment='openEuler版本的内核版本')
    publish_time = Column(TIMESTAMP(), comment='openEuler版本的发布日期')
    version_type = Column(String(), comment='openEuler社区成员的版本类型')



class PostgresDBMeta(type):
    _instances = {}
    _lock: Lock = Lock()

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


class PostgresDB(metaclass=PostgresDBMeta):

    def __init__(self, pg_url):
        self.engine = create_engine(
            pg_url,
            echo=False,
            pool_pre_ping=True)
        self.create_table()

    def create_table(self):
        Base.metadata.create_all(self.engine)

    def get_session(self):
        return sessionmaker(bind=self.engine)()

    def close(self):
        self.engine.dispose()
