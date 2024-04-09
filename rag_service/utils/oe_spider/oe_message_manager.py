# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from sqlalchemy import case, func
from datetime import datetime, timezone, timedelta

import pytz

from pg import PoStrageDB
from pg import OeCompatibilityOverallUnit, OeCompatibilityCard, OeCompatibilitySolution, OeCompatibilityOpenSourceSoftware, OeCompatibilityCommercialSoftware, OeCompatibilityOsv, OeCompatibilitySecurityNotice, OeCompatibilityCveDatabase


class OeMessageManager:
    @staticmethod
    def clear_oe_compatibility_overall_unit():
        try:
            with PoStrageDB().get_session() as session:
                session.query(OeCompatibilityOverallUnit).delete()
                session.commit()
        except Exception as e:
            return

    @staticmethod
    def add_oe_compatibility_overall_unit(info):
        oe_compatibility_overall_unit_slice = OeCompatibilityOverallUnit(
            id=info.get("id", ''),
            architecture=info.get("architecture", ''),
            bios_uefi=info.get("biosUefi", ''),
            certification_addr=info.get("certificationAddr", ''),
            certification_time=info.get("certificationTime", ''),
            commitid=info.get("commitID", ''),
            computer_type=info.get("computerType", ''),
            cpu=info.get("cpu", ''),
            date=info.get("date", ''),
            friendly_link=info.get("friendlyLink", ''),
            hard_disk_drive=info.get("hardDiskDrive", ''),
            hardware_factory=info.get("hardwareFactory", ''),
            hardware_model=info.get("hardwareModel", ''),
            host_bus_adapter=info.get("hostBusAdapter", ''),
            lang=info.get("lang", ''),
            main_board_bodel=info.get("mainboardModel", ''),
            openeuler_version =info.get("osVersion", '').replace(' ', '-'),
            ports_bus_types=info.get("portsBusTypes", ''),
            product_information=info.get("productInformation", ''),
            ram=info.get("ram", ''),
            video_adapter=info.get("videoAdapter", ''),
            compatibility_configuration=info.get("compatibilityConfiguration", ''),
            boardCards=info.get("boardCards", '')
        )
        try:
            with PoStrageDB().get_session() as session:
                session.add(oe_compatibility_overall_unit_slice)
                session.commit()
        except Exception as e:
            return

    @staticmethod
    def clear_oe_compatibility_card():
        try:
            with PoStrageDB().get_session() as session:
                session.query(OeCompatibilityCard).delete()
                session.commit()
        except Exception as e:
            return

    @staticmethod
    def add_oe_compatibility_card(info):
        oe_compatibility_card_slice = OeCompatibilityCard(
            id=info.get("id", ''),
            architecture=info.get("architecture", ''),
            board_model=info.get("boardModel", ''),
            chip_model=info.get("chipModel", ''),
            chip_vendor=info.get("chipVendor", ''),
            device_id=info.get("deviceID", ''),
            download_link=info.get("downloadLink", ''),
            driver_date=info.get("driverDate", ''),
            driver_name=info.get("driverName", ''),
            driver_size=info.get("driverSize", ''),
            item=info.get("item", ''),
            lang=info.get("lang", ''),
            openeuler_version =info.get("os", '').replace(' ', '-'),
            sha256=info.get("sha256", ''),
            ss_id=info.get("ssID", ''),
            sv_id=info.get("svID", ''),
            type=info.get("type", ''),
            vendor_id=info.get("vendorID", ''),
            version=info.get("version", '')
        )
        try:
            with PoStrageDB().get_session() as session:
                session.add(oe_compatibility_card_slice)
                session.commit()
        except Exception as e:
            return

    @staticmethod
    def clear_oe_compatibility_open_source_software():
        try:
            with PoStrageDB().get_session() as session:
                session.query(OeCompatibilityOpenSourceSoftware).delete()
                session.commit()
        except Exception as e:
            return

    @staticmethod
    def add_oe_compatibility_open_source_software(info):
        oe_compatibility_open_source_software_slice = OeCompatibilityOpenSourceSoftware(
            openeuler_version =info.get("os", '').replace(' ', '-'),
            arch=info.get("arch", ''),
            property=info.get("property", ''),
            result_url=info.get("result_url", ''),
            result_root=info.get("result_root", ''),
            bin=info.get("bin", ''),
            uninstall=info.get("uninstall", ''),
            license=info.get("license", ''),
            libs=info.get("libs", ''),
            install=info.get("install", ''),
            src_location=info.get("src_location", ''),
            group=info.get("group", ''),
            cmds=info.get("cmds", ''),
            type=info.get("type", ''),
            softwareName=info.get("softwareName", ''),
            category=info.get("category", ''),
            version=info.get("version", ''),
            downloadLink=info.get("downloadLink", '')
        )
        try:
            with PoStrageDB().get_session() as session:
                session.add(oe_compatibility_open_source_software_slice)
                session.commit()
        except Exception as e:
            return

    @staticmethod
    def clear_oe_compatibility_commercial_software():
        try:
            with PoStrageDB().get_session() as session:
                session.query(OeCompatibilityCommercialSoftware).delete()
                session.commit()
        except Exception as e:
            return

    @staticmethod
    def add_oe_compatibility_commercial_software(info):
        oe_compatibility_commercial_software_slice = OeCompatibilityCommercialSoftware(
            id=info.get("certId", ''),
            data_id=info.get("dataId", ''),
            type=info.get("type", ''),
            test_organization=info.get("testOrganization", ''),
            product_name=info.get("productName", ''),
            product_version=info.get("productVersion", ''),
            company_name=info.get("companyName", ''),
            platform_type_and_server_model=info.get("platformTypeAndServerModel", ''),
            authenticate_link=info.get("authenticateLink", ''),
            openeuler_version =(info.get("osName", '')+info.get("osVersion", '')).replace(' ', '-'),
            region=info.get("region", '')
        )
        try:
            with PoStrageDB().get_session() as session:
                session.add(oe_compatibility_commercial_software_slice)
                session.commit()
        except Exception as e:
            return

    @staticmethod
    def clear_oe_compatibility_solution():
        try:
            with PoStrageDB().get_session() as session:
                session.query(OeCompatibilitySolution).delete()
                session.commit()
        except Exception as e:
            return

    @staticmethod
    def add_oe_compatibility_solution(info):
        oe_compatibility_solution_slice = OeCompatibilitySolution(
            id=info.get("id", ''),
            architecture=info.get("architecture", ''),
            bios_uefi=info.get("biosUefi", ''),
            certification_type=info.get("certificationType", ''),
            cpu=info.get("cpu", ''),
            date=info.get("date", ''),
            driver=info.get("driver", ''),
            hard_disk_drive=info.get("hardDiskDrive", ''),
            introduce_link=info.get("introduceLink", ''),
            lang=info.get("lang", ''),
            libvirt_version=info.get("libvirtVersion", ''),
            network_card=info.get("networkCard", ''),
            openeuler_version =info.get("os", '').replace(' ', '-'),
            ovs_version=info.get("OVSVersion", ''),
            product=info.get("product", ''),
            qemu_version=info.get("qemuVersion", ''),
            raid=info.get("raid", ''),
            ram=info.get("ram", ''),
            server_model=info.get("serverModel", ''),
            server_vendor=info.get("serverVendor", ''),
            solution=info.get("solution", ''),
            stratovirt_version=info.get("stratovirtVersion", '')
        )
        try:
            with PoStrageDB().get_session() as session:
                session.add(oe_compatibility_solution_slice)
                session.commit()
        except Exception as e:
            return

    @staticmethod
    def clear_compatibility_osv():
        try:
            with PoStrageDB().get_session() as session:
                session.query(OeCompatibilityOsv).delete()
                session.commit()
        except Exception as e:
            return

    @staticmethod
    def add_oe_compatibility_osv(info):
        oe_compatibility_osv_slice = OeCompatibilityOsv(
            id=info.get("id", ''),
            arch=info.get("arch", ''),
            openeuler_version =info.get("osVersion", ''),
            osv_name=info.get("osvName", ''),
            date=info.get("date", ''),
            os_download_link=info.get("osDownloadLink", ''),
            type=info.get("id", ''),
            details=info.get("id", ''),
            friendly_link=info.get("friendlyLink", ''),
            total_result=info.get("totalResult", ''),
            checksum=info.get("checksum", ''),
            base_openeuler_version=info.get("baseOpeneulerVersion", '')
        )
        try:
            with PoStrageDB().get_session() as session:
                session.add(oe_compatibility_osv_slice)
                session.commit()
        except Exception as e:
            return

    @staticmethod
    def clear_oe_compatibility_security_notice():
        try:
            with PoStrageDB().get_session() as session:
                session.query(OeCompatibilitySecurityNotice).delete()
                session.commit()
        except Exception as e:
            return

    @staticmethod
    def add_oe_compatibility_security_notice(info):
        oe_compatibility_security_notice_slice = OeCompatibilitySecurityNotice(
            id=info.get("id", ''),
            affected_component=info.get("affectedComponent", ''),
            affected_product=info.get("affectedProduct", ''),
            announcement_time=info.get("announcementTime", ''),
            cve_id=info.get("cveId", ''),
            description=info.get("description", ''),
            introduction=info.get("introduction", ''),
            package_name=info.get("packageName", ''),
            reference_documents=info.get("referenceDocuments", ''),
            revision_history=info.get("revisionHistory", ''),
            security_notice_no=info.get("securityNoticeNo", ''),
            subject=info.get("subject", ''),
            summary=info.get("summary", ''),
            type=info.get("type", ''),
            notice_type=info.get("notice_type", ''),
            cvrf=info.get("cvrf", ''),
            package_helper_list=info.get("packageHelperList", ''),
            package_hotpatch_list=info.get("packageHotpatchList", ''),
            package_list=info.get("packageList", ''),
            reference_list=info.get("referenceList", ''),
            cve_list=info.get("cveList", '')
        )
        try:
            with PoStrageDB().get_session() as session:
                session.add(oe_compatibility_security_notice_slice)
                session.commit()
        except Exception as e:
            return

    @staticmethod
    def clear_oe_compatibility_cve_database():
        try:
            with PoStrageDB().get_session() as session:
                session.query(OeCompatibilityCveDatabase).delete()
                session.commit()
        except Exception as e:
            return

    @staticmethod
    def add_oe_compatibility_cve_database(info):
        oe_compatibility_cve_database_slice = OeCompatibilityCveDatabase(
            id=info.get("id", ''),
            affected_product=info.get("affectedProduct", ''),
            announcement_time=info.get("announcementTime", ''),
            attack_complexity_nvd=info.get("attackComplexityNVD", ''),
            attack_complexity_oe=info.get("attackVectorNVD", ''),
            attack_vector_nvd=info.get("attackVectorOE", ''),
            attack_vector_oe=info.get("attackVectorOE", ''),
            availability_nvd=info.get("availabilityNVD", ''),
            availability_oe=info.get("availabilityOE", ''),
            confidentiality_nvd=info.get("confidentialityNVD", ''),
            confidentiality_oe=info.get("confidentialityOE", ''),
            cve_id=info.get("cveId", ''),
            cvsss_core_nvd=info.get("cvsssCoreNVD", ''),
            cvsss_core_oe=info.get("cvsssCoreOE", ''),
            integrity_nvd=info.get("integrityNVD", ''),
            integrity_oe=info.get("integrityOE", ''),
            national_cyberAwareness_system=info.get("nationalCyberAwarenessSystem", ''),
            package_name=info.get("packageName", ''),
            privileges_required_nvd=info.get("privilegesRequiredNVD", ''),
            privileges_required_oe=info.get("privilegesRequiredOE", ''),
            scope_nvd=info.get("scopeNVD", ''),
            scope_oe=info.get("scopeOE", ''),
            status=info.get("status", ''),
            summary=info.get("summary", ''),
            type=info.get("type", ''),
            user_interaction_nvd=info.get("userInteractionNVD", ''),
            user_interactio_oe=info.get("userInteractionOE", ''),
            update_time=info.get("updateTime", ''),
            create_time=info.get("createTime", ''),
            security_notice_no=info.get("securityNoticeNo", ''),
            parser_bean=info.get("parserBean", ''),
            cvrf=info.get("cvrf", ''),
            package_list=info.get("packageList", '')
        )
        try:
            with PoStrageDB().get_session() as session:
                session.add(oe_compatibility_cve_database_slice)
                session.commit()
        except Exception as e:
            return
