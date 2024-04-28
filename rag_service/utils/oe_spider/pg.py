# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.

import os
from threading import Lock

from sqlalchemy import Column, String, BigInteger, TIMESTAMP, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from rag_service.security.config import config


Base = declarative_base()


class OeCompatibilityOverallUnit(Base):
    __tablename__ = 'oe_compatibility_overall_unit'
    __table_args__ = {'comment': 'openEuler支持的整机'}
    id = Column(BigInteger, primary_key=True)
    architecture = Column(String(), comment='架构')
    bios_uefi = Column(String())
    certification_addr = Column(String())
    certification_time = Column(String())
    commitid = Column(String())
    computer_type = Column(String())
    cpu = Column(String(), comment='CPU')
    date = Column(String(), comment='日期')
    friendly_link = Column(String())
    hard_disk_drive = Column(String())
    hardware_factory = Column(String(), comment='硬件厂家')
    hardware_model = Column(String(), comment='硬件型号')
    host_bus_adapter = Column(String())
    lang = Column(String())
    main_board_bodel = Column(String())
    openeuler_version  = Column(String(), comment='openEuler版本')
    ports_bus_types = Column(String())
    product_information = Column(String())
    ram = Column(String())
    update_time = Column(String())
    video_adapter = Column(String())
    compatibility_configuration = Column(String())
    boardCards = Column(String())

class OeCompatibilityCard(Base):
    __tablename__ = 'oe_compatibility_card'
    __table_args__ = {'comment': 'openEuler支持的板卡'}
    id = Column(BigInteger, primary_key=True)
    architecture = Column(String(), comment='架构')
    board_model = Column(String(), comment='板卡型号')
    chip_model = Column(String(), comment='芯片型号')
    chip_vendor = Column(String(), comment='芯片厂家')
    device_id = Column(String())
    download_link = Column(String())
    driver_date = Column(String())
    driver_name = Column(String(), comment='驱动名称')
    driver_size = Column(String())
    item = Column(String())
    lang = Column(String())
    openeuler_version  = Column(String(), comment='openEuler版本')
    sha256 = Column(String())
    ss_id = Column(String())
    sv_id = Column(String())
    type = Column(String(), comment='类型')
    vendor_id = Column(String())
    version = Column(String(), comment='版本')


class OeCompatibilityOpenSourceSoftware(Base):
    __tablename__ = 'oe_compatibility_open_source_software'
    __table_args__ = {'comment': 'openEuler支持的开源软件'}
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    openeuler_version  = Column(String(), comment='openEuler版本')
    arch = Column(String(), comment='架构')
    property = Column(String(), comment='软件属性')
    result_url = Column(String())
    result_root = Column(String())
    bin = Column(String())
    uninstall = Column(String())
    license = Column(String(), comment='开源协议')
    libs = Column(String())
    install = Column(String())
    src_location = Column(String())
    group = Column(String())
    cmds = Column(String())
    type = Column(String(), comment='软件类型')
    softwareName = Column(String())
    category = Column(String(), comment='软件名称')
    version = Column(String(), comment='版本')
    downloadLink = Column(String())


class OeCompatibilityCommercialSoftware(Base):
    __tablename__ = 'oe_compatibility_commercial_software'
    __table_args__ = {'comment': 'openEuler支持的商业软件'}
    id = Column(BigInteger, primary_key=True,)
    data_id = Column(String())
    type = Column(String(), comment='软件类型')
    test_organization = Column(String(), comment='测试机构')
    product_name = Column(String(), comment='软件名称')
    product_version = Column(String(), comment='软件版本')
    company_name = Column(String(), comment='厂家名称')
    platform_type_and_server_model = Column(String())
    authenticate_link = Column(String())
    openeuler_version  = Column(String(), comment='openEuler版本')
    region = Column(String())


class OeCompatibilitySolution(Base):
    __tablename__ = 'oe_compatibility_solution'
    __table_args__ = {'comment': 'openeuler支持的解决方案'}
    id = Column(String(), primary_key=True,)
    architecture = Column(String(), comment='架构')
    bios_uefi = Column(String())
    certification_type = Column(String(), comment='类型')
    cpu = Column(String())
    date = Column(String(), comment='日期')
    driver = Column(String())
    hard_disk_drive = Column(String())
    introduce_link = Column(String())
    lang = Column(String())
    libvirt_version = Column(String())
    network_card = Column(String())
    openeuler_version  = Column(String(), comment='openEuler版本')
    ovs_version = Column(String())
    product = Column(String(), comment='型号')
    qemu_version = Column(String())
    raid = Column(String())
    ram = Column(String())
    server_model = Column(String(), comment='厂家')
    server_vendor = Column(String())
    solution = Column(String(), comment='解决方案')
    stratovirt_version = Column(String())


class OeCompatibilityOsv(Base):
    __tablename__ = 'oe_compatibility_osv'
    id = Column(String(), primary_key=True,)
    arch = Column(String())
    openeuler_version  = Column(String())
    osv_name = Column(String())
    date = Column(String())
    os_download_link = Column(String())
    type = Column(String())
    details = Column(String())
    friendly_link = Column(String())
    total_result = Column(String())
    checksum = Column(String())
    base_openeuler_version = Column(String())


class OeCompatibilitySecurityNotice(Base):
    __tablename__ = 'oe_compatibility_security_notice'
    id = Column(String(), primary_key=True,)
    affected_component = Column(String())
    affected_product = Column(String())
    announcement_time = Column(String())
    cve_id = Column(String())
    description = Column(String())
    introduction = Column(String())
    package_name = Column(String())
    reference_documents = Column(String())
    revision_history = Column(String())
    security_notice_no = Column(String())
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


class OeCompatibilityCveDatabase(Base):
    __tablename__ = 'oe_compatibility_cve_database'
    id = Column(String(), primary_key=True,)
    affected_product = Column(String())
    announcement_time = Column(String())
    attack_complexity_nvd = Column(String())
    attack_complexity_oe = Column(String())
    attack_vector_nvd = Column(String())
    attack_vector_oe = Column(String())
    availability_nvd = Column(String())
    availability_oe = Column(String())
    confidentiality_nvd = Column(String())
    confidentiality_oe = Column(String())
    cve_id = Column(String())
    cvsss_core_nvd = Column(String())
    cvsss_core_oe = Column(String())
    integrity_nvd = Column(String())
    integrity_oe = Column(String())
    national_cyberAwareness_system = Column(String())
    package_name = Column(String())
    privileges_required_nvd = Column(String())
    privileges_required_oe = Column(String())
    scope_nvd = Column(String())
    scope_oe = Column(String())
    status = Column(String())
    summary = Column(String())
    type = Column(String())
    user_interaction_nvd = Column(String())
    user_interactio_oe = Column(String())
    update_time = Column(TIMESTAMP())
    create_time = Column(TIMESTAMP())
    security_notice_no = Column(String())
    parser_bean = Column(String())
    cvrf = Column(String())
    package_list = Column(String())


class PoStrageDBMeta(type):
    _instances = {}
    _lock: Lock = Lock()

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


class PoStrageDB(metaclass=PoStrageDBMeta):

    def __init__(self):
        self.engine = create_engine(
            f'postgresql+psycopg2://{config["POSTRAGE_USER"]}::{config["POSTRAGE_PWD"]}'
            f'@{config["POSTRAGE_HOST"]}/{config["POSTRAGE_DATABASE"]}',
            echo=False,
            pool_pre_ping=True)
        Base.metadata.create_all(self.engine)

    def get_session(self):
        return sessionmaker(bind=self.engine)()

    def close(self):
        self.engine.dispose()


with PoStrageDB().get_session() as session:
    session.query(1)
    pass
