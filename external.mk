# Keep one license text in the repository and include it in each local
# package's legal-info output, including its standalone source archive.
define FUXI_COPY_LICENSE
	$(INSTALL) -m 0644 $(BR2_EXTERNAL_FUXI_PATH)/LICENSE $($(PKG)_DIR)/LICENSE
endef

define FUXI_ARCHIVE_LICENSE
	rm -rf $($(PKG)_DIR)/.fuxi-legal-info
	mkdir -p $($(PKG)_DIR)/.fuxi-legal-info
	$(TAR) -xzf $($(PKG)_REDIST_SOURCES_DIR)/$($(PKG)_BASENAME_RAW).tar.gz \
		--strip-components=1 -C $($(PKG)_DIR)/.fuxi-legal-info
	$(INSTALL) -m 0644 $($(PKG)_DIR)/LICENSE $($(PKG)_DIR)/.fuxi-legal-info/LICENSE
	. support/download/helpers; cd $($(PKG)_DIR); TAR=$(TAR) mk_tar_gz \
		$($(PKG)_DIR)/.fuxi-legal-info \
		$($(PKG)_BASENAME_RAW) @0 \
		$($(PKG)_REDIST_SOURCES_DIR)/$($(PKG)_BASENAME_RAW).tar.gz
	rm -rf $($(PKG)_DIR)/.fuxi-legal-info
endef

include $(sort $(wildcard $(BR2_EXTERNAL_FUXI_PATH)/package/*/*.mk))
