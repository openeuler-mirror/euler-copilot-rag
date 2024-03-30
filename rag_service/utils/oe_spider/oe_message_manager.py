# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from sqlalchemy import case, func
from datetime import datetime, timezone, timedelta

import pytz

from pg import PoStrageDB
from pg import OeCompatibilityOverallUnit, OeCompatibilityCard, OeCompatibilitySolution, OeCompatibilityOpenSourceSoftware, OeCompatibilityCommercialSoftware, OeCompatibilityOsv

class OeMessageManager:
    @staticmethod
    def clear_oe_compatibility_overall_unit():
        try:
            with PoStrageDB().get_session() as session:
                session.query(OeCompatibilityOverallUnit).delete()  
                session.commit()
        except Exception as e:
            raise
    @staticmethod
    def add_oe_compatibility_overall_unit(info):
        oe_compatibility_overall_unit_slice = OeCompatibilityOverallUnit(
            id = info.get("id",None),
            architecture =  info.get("architecture",None),
            bios_uefi =  info.get("biosUefi",None),
            certification_addr =  info.get("certificationAddr",None),
            certification_time = info.get("certificationTime",None),
            commitid = info.get("commitID",None),
            computer_type = info.get("computerType",None),
            cpu = info.get("cpu",None),
            date = info.get("date",None),
            friendly_link = info.get("friendlyLink",None),
            hard_disk_drive = info.get("hardDiskDrive",None),
            hardware_factory = info.get("hardwareFactory",None),
            hardware_model = info.get("hardwareModel",None),
            host_bus_adapter = info.get("hostBusAdapter",None),
            lang = info.get("lang",None),
            main_board_bodel = info.get("mainboardModel",None),
            os_version = info.get("osVersion",None),
            ports_bus_types = info.get("portsBusTypes",None),
            product_information = info.get("productInformation",None),
            ram = info.get("ram",None),
            video_adapter = info.get("videoAdapter",None),
            compatibility_configuration =info.get("compatibilityConfiguration",None),
            boardCards=info.get("boardCards",None)
        )
        try:
            with PoStrageDB().get_session() as session:
                session.add(oe_compatibility_overall_unit_slice)
                session.commit()
        except Exception as e:
            raise
    @staticmethod
    def clear_oe_compatibility_card():
        try:
            with PoStrageDB().get_session() as session:
                session.query(OeCompatibilityCard).delete()  
                session.commit()
        except Exception as e:
            raise
    @staticmethod
    def add_oe_compatibility_card(info):
        oe_compatibility_card_slice = OeCompatibilityCard(
            id =  info.get("id",None),
            architecture =  info.get("architecture",None),
            board_model =  info.get("boardModel",None),
            chip_model =  info.get("chipModel",None),
            chip_vendor =  info.get("chipVendor",None),
            device_id =  info.get("deviceID",None),
            download_link =  info.get("downloadLink",None),
            driver_date =  info.get("driverDate",None),
            driver_name =  info.get("driverName",None),
            driver_size =  info.get("driverSize",None),
            item =  info.get("item",None),
            lang =  info.get("lang",None),
            os =  info.get("os",None),
            sha256 = info.get("sha256",None),
            ss_id =  info.get("ssID",None),
            sv_id =  info.get("svID",None),
            type =  info.get("type",None),
            vendor_id = info.get("vendorID",None),
            version =  info.get("version",None)
        )
        try:
            with PoStrageDB().get_session() as session:
                session.add(oe_compatibility_card_slice)
                session.commit()
        except Exception as e:
            raise
    @staticmethod
    def clear_oe_compatibility_open_source_software():
        try:
            with PoStrageDB().get_session() as session:
                session.query(OeCompatibilityOpenSourceSoftware).delete()  
                session.commit()
        except Exception as e:
            raise
    @staticmethod
    def add_oe_compatibility_open_source_software(info):
        oe_compatibility_open_source_software_slice = OeCompatibilityOpenSourceSoftware(
            os =  info.get("os",None),
            arch =  info.get("arch",None),
            property =  info.get("property",None),
            result_url =  info.get("result_url",None),
            result_root =  info.get("result_root",None),
            bin =  info.get("bin",None),
            uninstall =  info.get("uninstall",None),
            license =  info.get("license",None),
            libs =  info.get("libs",None),
            install =  info.get("install",None),
            src_location =  info.get("src_location",None),
            group =  info.get("group",None),
            cmds =  info.get("cmds",None),
            type =  info.get("type",None),
            softwareName =  info.get("softwareName",None),
            category =  info.get("category",None),
            version =  info.get("version",None),
            downloadLink =  info.get("downloadLink",None)
        )
        try:
            with PoStrageDB().get_session() as session:
                session.add(oe_compatibility_open_source_software_slice)
                session.commit()
        except Exception as e:
            raise
    @staticmethod
    def clear_oe_compatibility_commercial_software():
        try:
            with PoStrageDB().get_session() as session:
                session.query(OeCompatibilityCommercialSoftware).delete()  
                session.commit()
        except Exception as e:
            raise
    @staticmethod
    def add_oe_compatibility_commercial_software(info):
        oe_compatibility_commercial_software_slice = OeCompatibilityCommercialSoftware(
            id = info.get("certId",None),
            data_id = info.get("dataId",None),
            type = info.get("type",None),
            test_organization = info.get("testOrganization",None),
            product_name = info.get("productName",None),
            product_version = info.get("productVersion",None),
            company_name = info.get("companyName",None),
            platform_type_and_server_model = info.get("platformTypeAndServerModel",None),
            authenticate_link = info.get("authenticateLink",None),
            os_name = info.get("osName",None),
            os_version = info.get("osVersion",None),
            region = info.get("region",None)
        )
        try:
            with PoStrageDB().get_session() as session:
                session.add(oe_compatibility_commercial_software_slice)
                session.commit()
        except Exception as e:
            raise
    @staticmethod
    def clear_oe_compatibility_solution():
        try:
            with PoStrageDB().get_session() as session:
                session.query(OeCompatibilitySolution).delete()  
                session.commit()
        except Exception as e:
            raise
    @staticmethod
    def add_oe_compatibility_solution(info):
        oe_compatibility_solution_slice = OeCompatibilitySolution(
            id = info.get("id",None),
            architecture = info.get("architecture",None),
            bios_uefi = info.get("biosUefi",None),
            certification_type = info.get("certificationType",None),
            cpu = info.get("cpu",None),
            date = info.get("date",None),
            driver = info.get("driver",None),
            hard_disk_drive = info.get("hardDiskDrive",None),
            introduce_link = info.get("introduceLink",None),
            lang = info.get("lang",None),
            libvirt_version = info.get("libvirtVersion",None),
            network_card = info.get("networkCard",None),
            os = info.get("os",None),
            ovs_version = info.get("OVSVersion",None),
            product = info.get("product",None),
            qemu_version = info.get("qemuVersion",None),
            raid = info.get("raid",None),
            ram = info.get("ram",None),
            server_model = info.get("serverModel",None),
            server_vendor = info.get("serverVendor",None),    
            solution = info.get("solution",None),
            stratovirt_version = info.get("stratovirtVersion",None)
        )
        try:
            with PoStrageDB().get_session() as session:
                session.add(oe_compatibility_solution_slice)
                session.commit()
        except Exception as e:
            raise
    @staticmethod
    def clear_compatibility_osv():
        try:
            with PoStrageDB().get_session() as session:
                session.query(OeCompatibilityOsv).delete()  
                session.commit()
        except Exception as e:
            raise
    @staticmethod
    def add_oe_compatibility_osv(info):
        oe_compatibility_osv_slice = OeCompatibilityOsv(
            id = info.get("id",None),
            arch = info.get("arch",None),
            os_version = info.get("osVersion",None),
            osv_name = info.get("osvName",None),
            date = info.get("date",None),
            os_download_link = info.get("osDownloadLink",None),
            type = info.get("id",None),
            details = info.get("id",None),
            friendly_link = info.get("friendlyLink",None),
            total_result = info.get("totalResult",None),
            checksum = info.get("checksum",None),
            base_openeuler_version = info.get("baseOpeneulerVersion",None)
        )
        try:
            with PoStrageDB().get_session() as session:
                session.add(oe_compatibility_osv_slice)
                session.commit()
        except Exception as e:
            raise