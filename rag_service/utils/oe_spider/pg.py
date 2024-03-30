# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.

import os
from threading import Lock

import pytz
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column,String, BigInteger, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


Base = declarative_base()


class OeCompatibilityOverallUnit(Base):
    __tablename__ = 'oe_compatibility_overall_unit'
    id = Column(BigInteger, primary_key=True)
    architecture = Column(String())
    bios_uefi = Column(String())
    certification_addr = Column(String())
    certification_time = Column(String())
    commitid = Column(String())
    computer_type = Column(String())
    cpu = Column(String())
    date = Column(String())
    friendly_link = Column(String())
    hard_disk_drive = Column(String())
    hardware_factory = Column(String())
    hardware_model = Column(String())
    host_bus_adapter = Column(String())
    lang = Column(String())
    main_board_bodel = Column(String())
    os_version = Column(String())
    ports_bus_types = Column(String())
    product_information = Column(String())
    ram = Column(String())
    update_time = Column(String())
    video_adapter = Column(String())
    compatibility_configuration = Column(String())
    boardCards = Column(String())


class OeCompatibilityCard(Base):
    __tablename__ = 'oe_compatibility_card'
    id = Column(BigInteger, primary_key=True)
    architecture = Column(String())
    board_model = Column(String())
    chip_model = Column(String())
    chip_vendor = Column(String())
    device_id = Column(String())
    download_link = Column(String())
    driver_date = Column(String())
    driver_name = Column(String())
    driver_size = Column(String())
    item = Column(String())
    lang = Column(String())
    os = Column(String())
    sha256 = Column(String())
    ss_id = Column(String())
    sv_id = Column(String())
    type = Column(String())
    vendor_id = Column(String())
    version = Column(String())


class OeCompatibilityOpenSourceSoftware(Base):
    __tablename__ = 'oe_compatibility_open_source_software'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    os = Column(String())
    arch = Column(String())
    property = Column(String())
    result_url = Column(String())
    result_root = Column(String())
    bin = Column(String())
    uninstall = Column(String())
    license = Column(String())
    libs = Column(String())
    install = Column(String())
    src_location = Column(String())
    group = Column(String())
    cmds = Column(String())
    type = Column(String())
    softwareName = Column(String())
    category = Column(String())
    version = Column(String())
    downloadLink = Column(String())


class OeCompatibilityCommercialSoftware(Base):
    __tablename__ = 'oe_compatibility_commercial_software'
    id = Column(BigInteger, primary_key=True,)
    data_id = Column(String())
    type = Column(String())
    test_organization = Column(String())
    product_name = Column(String())
    product_version = Column(String())
    company_name = Column(String())
    platform_type_and_server_model = Column(String())
    authenticate_link = Column(String())
    os_name = Column(String())
    os_version = Column(String())
    region = Column(String())


class OeCompatibilitySolution(Base):
    __tablename__ = 'oe_compatibility_solution'
    id = Column(String(), primary_key=True,)
    architecture = Column(String())
    bios_uefi = Column(String())
    certification_type = Column(String())
    cpu = Column(String())
    date = Column(String())
    driver = Column(String())
    hard_disk_drive = Column(String())
    introduce_link = Column(String())
    lang = Column(String())
    libvirt_version = Column(String())
    network_card = Column(String())
    os = Column(String())
    ovs_version = Column(String())
    product = Column(String())
    qemu_version = Column(String())
    raid = Column(String())
    ram = Column(String())
    server_model = Column(String())
    server_vendor = Column(String())    
    solution = Column(String())
    stratovirt_version = Column(String())


class OeCompatibilityOsv(Base):
    __tablename__ = 'oe_compatibility_osv'
    id = Column(String(), primary_key=True,)
    arch = Column(String())
    os_version = Column(String())
    osv_name = Column(String())
    date = Column(String())
    os_download_link = Column(String())
    type = Column(String())
    details = Column(String())
    friendly_link = Column(String())
    total_result = Column(String())
    checksum = Column(String())
    base_openeuler_version = Column(String())


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
                f'postgresql+psycopg2://{os.getenv("POSTRAGE_USER")}::{os.getenv("POSTRAGE_PWD")}'
                f'@{os.getenv("POSTRAGE_HOST")}/{os.getenv("POSTRAGE_DATABASE")}',
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
