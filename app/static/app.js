"use strict";


/* =========================================================
   VANTA CLOUD
   MAIN FRONTEND JAVASCRIPT
   ========================================================= */


/*
 * Browsers can restore the Cloud page from their
 * back-forward cache.
 *
 * If Settings changed while Home was cached, force one
 * fresh request so the new permissions/theme/default view
 * are reflected immediately.
 */
window.addEventListener(
    "pageshow",
    (event) => {

        if (event.persisted) {

            window.location.reload();

        }

    }
);


document.addEventListener(
    "DOMContentLoaded",
    () => {


        /* =====================================================
           ROOT SETTINGS
           ===================================================== */

        const appRoot =
            document.documentElement;


        const defaultView =
            appRoot.dataset.defaultView
            ||
            "recent";


        /* =====================================================
           ELEMENT REFERENCES
           ===================================================== */

        const accountButton =
            document.getElementById(
                "accountButton"
            );


        const accountDropdown =
            document.getElementById(
                "accountDropdown"
            );


        const searchInput =
            document.getElementById(
                "searchInput"
            );


        const searchClear =
            document.getElementById(
                "searchClear"
            );


        const searchSuggestions =
            document.getElementById(
                "searchSuggestions"
            );


        const categoryButtons =
            Array.from(
                document.querySelectorAll(
                    "[data-category]"
                )
            );


        const fileCount =
            document.getElementById(
                "fileCount"
            );


        const filesHeading =
            document.getElementById(
                "filesHeading"
            );


        const noResults =
            document.getElementById(
                "noResults"
            );


        const filesSection =
            document.getElementById(
                "filesSection"
            );


        /* =====================================================
           UPLOAD REFERENCES
           ===================================================== */

        const openUploadButton =
            document.getElementById(
                "openUploadButton"
            );


        const uploadModal =
            document.getElementById(
                "uploadModal"
            );


        const closeUploadButton =
            document.getElementById(
                "closeUploadButton"
            );


        const cancelUploadButton =
            document.getElementById(
                "cancelUploadButton"
            );


        const uploadForm =
            document.getElementById(
                "uploadForm"
            );


        const fileInput =
            document.getElementById(
                "fileInput"
            );


        const dropZone =
            document.getElementById(
                "dropZone"
            );


        const uploadSelection =
            document.getElementById(
                "uploadSelection"
            );


        const selectedFileCount =
            document.getElementById(
                "selectedFileCount"
            );


        const uploadFileList =
            document.getElementById(
                "uploadFileList"
            );


        const uploadSubmitButton =
            document.getElementById(
                "uploadSubmitButton"
            );


        /* =====================================================
           RENAME REFERENCES
           ===================================================== */

        const renameModal =
            document.getElementById(
                "renameModal"
            );


        const renameForm =
            document.getElementById(
                "renameForm"
            );


        const renameInput =
            document.getElementById(
                "renameInput"
            );


        const closeRenameButton =
            document.getElementById(
                "closeRenameButton"
            );


        const cancelRenameButton =
            document.getElementById(
                "cancelRenameButton"
            );


        /* =====================================================
           TOAST
           ===================================================== */

        const toast =
            document.getElementById(
                "toast"
            );


        /* =====================================================
           SERVER-SUPPLIED UPLOAD SETTINGS
           ===================================================== */

        const maxUploadMb =
            Number(
                fileInput
                    ?.dataset
                    .maxUploadMb
                ||
                0
            );


        const maxUploadBytes =
            maxUploadMb > 0

                ? (
                    maxUploadMb
                    *
                    1024
                    *
                    1024
                )

                : 0;


        const multipleUploadsAllowed =
            Boolean(
                fileInput?.multiple
            );


        /* =====================================================
           APP STATE
           ===================================================== */

        let activeCategory =
            "all";


        let currentSearch =
            "";


        let currentSuggestions =
            [];


        let selectedSuggestionIndex =
            -1;


        let toastTimer =
            null;


        let renameOriginalName =
            "";


        /* =====================================================
           TOAST HELPER
           ===================================================== */

        function showToast(
            message,
            duration = 2800
        ) {

            if (!toast) {

                return;

            }


            if (toastTimer) {

                window.clearTimeout(
                    toastTimer
                );

            }


            toast.textContent =
                message;


            toast.hidden =
                false;


            toastTimer =
                window.setTimeout(
                    () => {

                        toast.hidden =
                            true;

                    },
                    duration
                );

        }


        /* =====================================================
           BODY SCROLL
           ===================================================== */

        function updateBodyScrollLock() {

            const uploadOpen =
                uploadModal
                &&
                !uploadModal.hidden;


            const renameOpen =
                renameModal
                &&
                !renameModal.hidden;


            document.body.style.overflow =
                (
                    uploadOpen
                    ||
                    renameOpen
                )

                    ? "hidden"

                    : "";

        }


        /* =====================================================
           FILE CARD HELPER
           ===================================================== */

        function getFileCards() {

            return Array.from(
                document.querySelectorAll(
                    "[data-file-card]"
                )
            );

        }


        /* =====================================================
           ACCOUNT DROPDOWN
           ===================================================== */

        function closeAccountDropdown() {

            if (!accountDropdown) {

                return;

            }


            accountDropdown.hidden =
                true;


            if (accountButton) {

                accountButton.setAttribute(
                    "aria-expanded",
                    "false"
                );

            }

        }


        function openAccountDropdown() {

            if (!accountDropdown) {

                return;

            }


            closeAllFileMenus();

            closeSearchSuggestions();


            accountDropdown.hidden =
                false;


            if (accountButton) {

                accountButton.setAttribute(
                    "aria-expanded",
                    "true"
                );

            }

        }


        if (
            accountButton
            &&
            accountDropdown
        ) {

            accountButton.addEventListener(
                "click",
                (event) => {

                    event.stopPropagation();


                    if (
                        accountDropdown.hidden
                    ) {

                        openAccountDropdown();

                    } else {

                        closeAccountDropdown();

                    }

                }
            );

        }


        /* =====================================================
           FILE MENUS
           ===================================================== */

        function closeAllFileMenus(
            exceptMenu = null
        ) {

            const menus =
                document.querySelectorAll(
                    ".file-menu"
                );


            menus.forEach(
                (menu) => {

                    if (
                        menu
                        ===
                        exceptMenu
                    ) {

                        return;

                    }


                    menu.hidden =
                        true;


                    const wrapper =
                        menu.closest(
                            ".file-menu-wrap"
                        );


                    const button =
                        wrapper
                            ?.querySelector(
                                ".file-menu-button"
                            );


                    if (button) {

                        button.setAttribute(
                            "aria-expanded",
                            "false"
                        );

                    }

                }
            );

        }


        const fileMenuButtons =
            document.querySelectorAll(
                ".file-menu-button"
            );


        fileMenuButtons.forEach(
            (button) => {

                button.addEventListener(
                    "click",
                    (event) => {

                        event.stopPropagation();


                        closeAccountDropdown();

                        closeSearchSuggestions();


                        const wrapper =
                            button.closest(
                                ".file-menu-wrap"
                            );


                        const menu =
                            wrapper
                                ?.querySelector(
                                    ".file-menu"
                                );


                        if (!menu) {

                            return;

                        }


                        const shouldOpen =
                            menu.hidden;


                        closeAllFileMenus();


                        menu.hidden =
                            !shouldOpen;


                        button.setAttribute(
                            "aria-expanded",
                            shouldOpen
                                ? "true"
                                : "false"
                        );

                    }
                );

            }
        );


        /* =====================================================
           FILE COUNT
           ===================================================== */

        function updateFileCount(
            count
        ) {

            if (!fileCount) {

                return;

            }


            fileCount.textContent =
                `${count} ${
                    count === 1
                        ? "item"
                        : "items"
                }`;

        }


        /* =====================================================
           FILE SECTION HEADING
           ===================================================== */

        function updateFileHeading() {

            if (!filesHeading) {

                return;

            }


            if (
                currentSearch !== ""
            ) {

                filesHeading.textContent =
                    "Search results";

                return;

            }


            if (
                activeCategory
                !==
                "all"
            ) {

                filesHeading.textContent =
                    activeCategory;

                return;

            }


            filesHeading.textContent =
                "Recent files";

        }


        /* =====================================================
           FILE FILTERING
           ===================================================== */

        function applyFilters() {

            const fileCards =
                getFileCards();


            let visibleCount =
                0;


            fileCards.forEach(
                (card) => {

                    const name =
                        (
                            card.dataset.name
                            ||
                            ""
                        )
                            .toLowerCase();


                    const category =
                        card.dataset.category
                        ||
                        "";


                    const matchesSearch =
                        (
                            currentSearch
                            ===
                            ""
                        )
                        ||
                        name.includes(
                            currentSearch
                        );


                    const matchesCategory =
                        (
                            activeCategory
                            ===
                            "all"
                        )
                        ||
                        (
                            category
                            ===
                            activeCategory
                        );


                    const visible =
                        matchesSearch
                        &&
                        matchesCategory;


                    card.classList.toggle(
                        "is-hidden",
                        !visible
                    );


                    if (visible) {

                        visibleCount +=
                            1;

                    }

                }
            );


            updateFileCount(
                visibleCount
            );


            updateFileHeading();


            if (noResults) {

                noResults.hidden =
                    visibleCount
                    !==
                    0;

            }

        }


        /* =====================================================
           SEARCH SUGGESTIONS
           ===================================================== */

        function closeSearchSuggestions() {

            if (!searchSuggestions) {

                return;

            }


            searchSuggestions.hidden =
                true;


            selectedSuggestionIndex =
                -1;


            if (searchInput) {

                searchInput.setAttribute(
                    "aria-expanded",
                    "false"
                );

            }

        }


        function getMatchingSuggestions() {

            if (
                currentSearch
                ===
                ""
            ) {

                return [];

            }


            return getFileCards()

                .filter(
                    (card) => {

                        const name =
                            (
                                card.dataset.name
                                ||
                                ""
                            )
                                .toLowerCase();


                        return name.includes(
                            currentSearch
                        );

                    }
                )

                .slice(
                    0,
                    8
                );

        }


        function updateSuggestionHighlight() {

            if (!searchSuggestions) {

                return;

            }


            const buttons =
                Array.from(
                    searchSuggestions
                        .querySelectorAll(
                            ".search-suggestion"
                        )
                );


            buttons.forEach(
                (
                    button,
                    index
                ) => {

                    const active =
                        index
                        ===
                        selectedSuggestionIndex;


                    button.classList.toggle(
                        "active",
                        active
                    );


                    button.setAttribute(
                        "aria-selected",
                        active
                            ? "true"
                            : "false"
                    );

                }
            );


            const activeButton =
                buttons[
                    selectedSuggestionIndex
                ];


            if (activeButton) {

                activeButton.scrollIntoView(
                    {
                        block:
                            "nearest",
                    }
                );

            }

        }


        function resetCategoryButtons() {

            activeCategory =
                "all";


            categoryButtons.forEach(
                (button) => {

                    button.classList.toggle(
                        "active",
                        button.dataset.category
                        ===
                        "all"
                    );

                }
            );

        }


        function selectSearchSuggestion(
            card
        ) {

            if (
                !card
                ||
                !searchInput
            ) {

                return;

            }


            const fileNameElement =
                card.querySelector(
                    ".file-name"
                );


            const fileName =
                fileNameElement
                    ?.textContent
                    ?.trim()
                ||
                card.dataset.name
                ||
                "";


            searchInput.value =
                fileName;


            currentSearch =
                fileName
                    .toLowerCase();


            if (searchClear) {

                searchClear.hidden =
                    false;

            }


            resetCategoryButtons();


            applyFilters();

            closeSearchSuggestions();


            card.scrollIntoView(
                {
                    behavior:
                        "smooth",

                    block:
                        "center",
                }
            );


            card.classList.remove(
                "search-highlight"
            );


            window.requestAnimationFrame(
                () => {

                    card.classList.add(
                        "search-highlight"
                    );

                }
            );


            window.setTimeout(
                () => {

                    card.classList.remove(
                        "search-highlight"
                    );

                },
                1800
            );

        }


        function renderSearchSuggestions() {

            if (!searchSuggestions) {

                return;

            }


            currentSuggestions =
                getMatchingSuggestions();


            searchSuggestions.innerHTML =
                "";


            selectedSuggestionIndex =
                -1;


            if (
                currentSearch
                ===
                ""
                ||
                currentSuggestions.length
                ===
                0
            ) {

                closeSearchSuggestions();

                return;

            }


            currentSuggestions.forEach(
                (card) => {

                    const fileNameElement =
                        card.querySelector(
                            ".file-name"
                        );


                    const fileName =
                        fileNameElement
                            ?.textContent
                            ?.trim()
                        ||
                        card.dataset.name
                        ||
                        "File";


                    const category =
                        card.dataset.category
                        ||
                        "Other";


                    const metaElement =
                        card.querySelector(
                            ".file-meta"
                        );


                    const metaText =
                        metaElement
                            ?.textContent
                            ?.replace(
                                /\s+/g,
                                " "
                            )
                            ?.trim()
                        ||
                        "Vanta Cloud file";


                    const button =
                        document.createElement(
                            "button"
                        );


                    button.type =
                        "button";


                    button.className =
                        "search-suggestion";


                    button.setAttribute(
                        "role",
                        "option"
                    );


                    button.setAttribute(
                        "aria-selected",
                        "false"
                    );


                    const copy =
                        document.createElement(
                            "span"
                        );


                    copy.className =
                        "search-suggestion-copy";


                    const name =
                        document.createElement(
                            "span"
                        );


                    name.className =
                        "search-suggestion-name";


                    name.textContent =
                        fileName;


                    const meta =
                        document.createElement(
                            "span"
                        );


                    meta.className =
                        "search-suggestion-meta";


                    meta.textContent =
                        metaText;


                    const categoryBadge =
                        document.createElement(
                            "span"
                        );


                    categoryBadge.className =
                        "search-suggestion-category";


                    categoryBadge.textContent =
                        category;


                    copy.append(
                        name,
                        meta
                    );


                    button.append(
                        copy,
                        categoryBadge
                    );


                    button.addEventListener(
                        "click",
                        () => {

                            selectSearchSuggestion(
                                card
                            );

                        }
                    );


                    searchSuggestions.appendChild(
                        button
                    );

                }
            );


            searchSuggestions.hidden =
                false;


            if (searchInput) {

                searchInput.setAttribute(
                    "aria-expanded",
                    "true"
                );

            }

        }


        /* =====================================================
           SEARCH INPUT
           ===================================================== */

        if (searchInput) {

            searchInput.addEventListener(
                "input",
                () => {

                    currentSearch =
                        searchInput.value
                            .trim()
                            .toLowerCase();


                    if (searchClear) {

                        searchClear.hidden =
                            currentSearch
                            ===
                            "";

                    }


                    applyFilters();

                    renderSearchSuggestions();

                }
            );


            searchInput.addEventListener(
                "focus",
                () => {

                    if (
                        currentSearch
                        !==
                        ""
                    ) {

                        renderSearchSuggestions();

                    }

                }
            );


            searchInput.addEventListener(
                "keydown",
                (event) => {

                    if (
                        event.key
                        ===
                        "Escape"
                    ) {

                        closeSearchSuggestions();

                        return;

                    }


                    if (
                        !searchSuggestions
                        ||
                        searchSuggestions.hidden
                        ||
                        currentSuggestions.length
                        ===
                        0
                    ) {

                        return;

                    }


                    if (
                        event.key
                        ===
                        "ArrowDown"
                    ) {

                        event.preventDefault();


                        selectedSuggestionIndex +=
                            1;


                        if (
                            selectedSuggestionIndex
                            >=
                            currentSuggestions.length
                        ) {

                            selectedSuggestionIndex =
                                0;

                        }


                        updateSuggestionHighlight();

                        return;

                    }


                    if (
                        event.key
                        ===
                        "ArrowUp"
                    ) {

                        event.preventDefault();


                        selectedSuggestionIndex -=
                            1;


                        if (
                            selectedSuggestionIndex
                            <
                            0
                        ) {

                            selectedSuggestionIndex =
                                currentSuggestions.length
                                -
                                1;

                        }


                        updateSuggestionHighlight();

                        return;

                    }


                    if (
                        event.key
                        ===
                        "Enter"
                        &&
                        selectedSuggestionIndex
                        >=
                        0
                    ) {

                        const selectedCard =
                            currentSuggestions[
                                selectedSuggestionIndex
                            ];


                        if (selectedCard) {

                            event.preventDefault();


                            selectSearchSuggestion(
                                selectedCard
                            );

                        }

                    }

                }
            );

        }


        /* =====================================================
           SEARCH CLEAR
           ===================================================== */

        if (
            searchClear
            &&
            searchInput
        ) {

            searchClear.addEventListener(
                "click",
                () => {

                    searchInput.value =
                        "";


                    currentSearch =
                        "";


                    searchClear.hidden =
                        true;


                    closeSearchSuggestions();

                    applyFilters();

                    searchInput.focus();

                }
            );

        }


        /* =====================================================
           CATEGORY FILTERING
           ===================================================== */

        categoryButtons.forEach(
            (button) => {

                button.addEventListener(
                    "click",
                    () => {

                        const category =
                            button.dataset.category;


                        if (!category) {

                            return;

                        }


                        activeCategory =
                            category;


                        categoryButtons.forEach(
                            (otherButton) => {

                                otherButton
                                    .classList
                                    .remove(
                                        "active"
                                    );

                            }
                        );


                        button.classList.add(
                            "active"
                        );


                        applyFilters();

                        closeSearchSuggestions();


                        if (filesSection) {

                            filesSection.scrollIntoView(
                                {
                                    behavior:
                                        "smooth",

                                    block:
                                        "start",
                                }
                            );

                        }

                    }
                );

            }
        );


        /* =====================================================
           FILENAME EXTENSION HELPER
           ===================================================== */

        function getFilenameExtension(
            filename
        ) {

            const lastDot =
                filename.lastIndexOf(
                    "."
                );


            if (
                lastDot <= 0
                ||
                lastDot
                ===
                filename.length - 1
            ) {

                return "";

            }


            return filename
                .slice(
                    lastDot
                )
                .toLowerCase();

        }


        /* =====================================================
           RENAME MODAL
           ===================================================== */

        function openRenameModal(
            fileId,
            fileName
        ) {

            if (
                !renameModal
                ||
                !renameForm
                ||
                !renameInput
            ) {

                return;

            }


            if (
                uploadModal
                &&
                !uploadModal.hidden
            ) {

                closeUploadModal();

            }


            closeAccountDropdown();

            closeAllFileMenus();

            closeSearchSuggestions();


            renameOriginalName =
                fileName;


            renameForm.action =
                `/files/${
                    encodeURIComponent(
                        fileId
                    )
                }/rename`;


            renameInput.value =
                fileName;


            renameModal.hidden =
                false;


            updateBodyScrollLock();


            window.setTimeout(
                () => {

                    renameInput.focus();


                    const dotIndex =
                        fileName.lastIndexOf(
                            "."
                        );


                    if (
                        dotIndex > 0
                    ) {

                        renameInput.setSelectionRange(
                            0,
                            dotIndex
                        );

                    } else {

                        renameInput.select();

                    }

                },
                0
            );

        }


        function closeRenameModal() {

            if (!renameModal) {

                return;

            }


            renameModal.hidden =
                true;


            if (renameForm) {

                renameForm.action =
                    "";

            }


            if (renameInput) {

                renameInput.value =
                    "";

            }


            renameOriginalName =
                "";


            updateBodyScrollLock();

        }


        /* =====================================================
           RENAME BUTTONS
           ===================================================== */

        const renameButtons =
            document.querySelectorAll(
                "[data-rename-button]"
            );


        renameButtons.forEach(
            (button) => {

                button.addEventListener(
                    "click",
                    () => {

                        const fileId =
                            button.dataset.fileId;


                        const fileName =
                            button.dataset.fileName;


                        if (
                            !fileId
                            ||
                            !fileName
                        ) {

                            return;

                        }


                        openRenameModal(
                            fileId,
                            fileName
                        );

                    }
                );

            }
        );


        /* =====================================================
           RENAME CLOSE CONTROLS
           ===================================================== */

        if (closeRenameButton) {

            closeRenameButton.addEventListener(
                "click",
                closeRenameModal
            );

        }


        if (cancelRenameButton) {

            cancelRenameButton.addEventListener(
                "click",
                closeRenameModal
            );

        }


        if (renameModal) {

            renameModal.addEventListener(
                "click",
                (event) => {

                    if (
                        event.target
                        ===
                        renameModal
                    ) {

                        closeRenameModal();

                    }

                }
            );

        }


        /* =====================================================
           RENAME SUBMISSION
           ===================================================== */

        if (
            renameForm
            &&
            renameInput
        ) {

            renameForm.addEventListener(
                "submit",
                (event) => {

                    const newName =
                        renameInput.value
                            .trim();


                    if (!newName) {

                        event.preventDefault();


                        showToast(
                            "Enter a filename."
                        );


                        renameInput.focus();

                        return;

                    }


                    if (
                        newName
                        ===
                        "."
                        ||
                        newName
                        ===
                        ".."
                    ) {

                        event.preventDefault();


                        showToast(
                            "That filename is not valid."
                        );


                        renameInput.focus();

                        return;

                    }


                    const originalExtension =
                        getFilenameExtension(
                            renameOriginalName
                        );


                    const newExtension =
                        getFilenameExtension(
                            newName
                        );


                    if (
                        originalExtension
                        !==
                        newExtension
                    ) {

                        event.preventDefault();


                        showToast(
                            originalExtension

                                ? (
                                    `Keep the original ${originalExtension} extension.`
                                )

                                : (
                                    "Do not add a file extension."
                                )
                        );


                        renameInput.focus();

                        return;

                    }


                    const submitButton =
                        renameForm.querySelector(
                            "button[type='submit']"
                        );


                    if (submitButton) {

                        submitButton.disabled =
                            true;


                        submitButton.textContent =
                            "Renaming...";

                    }

                }
            );

        }


        /* =====================================================
           UPLOAD MODAL
           ===================================================== */

        function openUploadModal() {

            if (!uploadModal) {

                return;

            }


            if (
                renameModal
                &&
                !renameModal.hidden
            ) {

                closeRenameModal();

            }


            closeAccountDropdown();

            closeAllFileMenus();

            closeSearchSuggestions();


            uploadModal.hidden =
                false;


            updateBodyScrollLock();

        }


        function closeUploadModal() {

            if (!uploadModal) {

                return;

            }


            uploadModal.hidden =
                true;


            updateBodyScrollLock();

        }


        if (openUploadButton) {

            openUploadButton.addEventListener(
                "click",
                openUploadModal
            );

        }


        if (closeUploadButton) {

            closeUploadButton.addEventListener(
                "click",
                closeUploadModal
            );

        }


        if (cancelUploadButton) {

            cancelUploadButton.addEventListener(
                "click",
                closeUploadModal
            );

        }


        if (uploadModal) {

            uploadModal.addEventListener(
                "click",
                (event) => {

                    if (
                        event.target
                        ===
                        uploadModal
                    ) {

                        closeUploadModal();

                    }

                }
            );

        }


        /* =====================================================
           FORMAT FILE SIZE
           ===================================================== */

        function formatFileSize(
            bytes
        ) {

            if (
                !Number.isFinite(
                    bytes
                )
                ||
                bytes < 0
            ) {

                return "";

            }


            if (
                bytes < 1024
            ) {

                return `${bytes} B`;

            }


            const units = [
                "KB",
                "MB",
                "GB",
                "TB",
            ];


            let value =
                bytes
                /
                1024;


            for (
                let index = 0;
                index < units.length;
                index += 1
            ) {

                if (
                    value < 1024
                    ||
                    index
                    ===
                    units.length - 1
                ) {

                    return (
                        `${value.toFixed(1)} ${units[index]}`
                    );

                }


                value /=
                    1024;

            }


            return `${bytes} B`;

        }


        /* =====================================================
           UPLOAD VALIDATION
           ===================================================== */

        function getUploadValidation(
            files
        ) {

            const invalidIndexes =
                new Set();


            let message =
                "";


            if (
                !multipleUploadsAllowed
                &&
                files.length > 1
            ) {

                files.forEach(
                    (
                        _file,
                        index
                    ) => {

                        if (
                            index > 0
                        ) {

                            invalidIndexes.add(
                                index
                            );

                        }

                    }
                );


                message =
                    "Multiple file uploads are disabled.";

            }


            files.forEach(
                (
                    selectedFile,
                    index
                ) => {

                    if (
                        maxUploadBytes > 0
                        &&
                        selectedFile.size
                        >
                        maxUploadBytes
                    ) {

                        invalidIndexes.add(
                            index
                        );


                        if (!message) {

                            message =
                                `"${selectedFile.name}" exceeds the ${maxUploadMb} MB limit.`;

                        }

                    }

                }
            );


            return {

                valid:
                    invalidIndexes.size
                    ===
                    0,

                invalidIndexes,

                message,

            };

        }


        /* =====================================================
           SELECTED UPLOAD FILES
           ===================================================== */

        function renderSelectedFiles() {

            if (
                !fileInput
                ||
                !uploadSelection
                ||
                !uploadFileList
                ||
                !selectedFileCount
            ) {

                return;

            }


            const files =
                Array.from(
                    fileInput.files
                    ||
                    []
                );


            uploadFileList.innerHTML =
                "";


            if (
                files.length
                ===
                0
            ) {

                uploadSelection.hidden =
                    true;


                selectedFileCount.textContent =
                    "0 files";


                if (uploadSubmitButton) {

                    uploadSubmitButton.disabled =
                        true;

                }


                return;

            }


            const validation =
                getUploadValidation(
                    files
                );


            uploadSelection.hidden =
                false;


            selectedFileCount.textContent =
                `${files.length} ${
                    files.length === 1
                        ? "file"
                        : "files"
                }`;


            files.forEach(
                (
                    selectedFile,
                    index
                ) => {

                    const item =
                        document.createElement(
                            "div"
                        );


                    item.className =
                        "upload-file-item";


                    if (
                        validation
                            .invalidIndexes
                            .has(
                                index
                            )
                    ) {

                        item.classList.add(
                            "is-invalid"
                        );

                    }


                    const name =
                        document.createElement(
                            "span"
                        );


                    name.className =
                        "upload-file-item-name";


                    name.textContent =
                        selectedFile.name;


                    const size =
                        document.createElement(
                            "span"
                        );


                    size.className =
                        "upload-file-item-size";


                    size.textContent =
                        formatFileSize(
                            selectedFile.size
                        );


                    item.append(
                        name,
                        size
                    );


                    uploadFileList.appendChild(
                        item
                    );

                }
            );


            if (uploadSubmitButton) {

                uploadSubmitButton.disabled =
                    !validation.valid;

            }

        }


        if (fileInput) {

            fileInput.addEventListener(
                "change",
                () => {

                    renderSelectedFiles();


                    const files =
                        Array.from(
                            fileInput.files
                            ||
                            []
                        );


                    const validation =
                        getUploadValidation(
                            files
                        );


                    if (
                        files.length > 0
                        &&
                        !validation.valid
                        &&
                        validation.message
                    ) {

                        showToast(
                            validation.message
                        );

                    }

                }
            );

        }


        /* =====================================================
           DRAG AND DROP
           ===================================================== */

        if (
            dropZone
            &&
            fileInput
        ) {

            [
                "dragenter",
                "dragover",
            ].forEach(
                (eventName) => {

                    dropZone.addEventListener(
                        eventName,
                        (event) => {

                            event.preventDefault();

                            event.stopPropagation();


                            dropZone.classList.add(
                                "drag-active"
                            );

                        }
                    );

                }
            );


            [
                "dragleave",
                "drop",
            ].forEach(
                (eventName) => {

                    dropZone.addEventListener(
                        eventName,
                        (event) => {

                            event.preventDefault();

                            event.stopPropagation();


                            dropZone.classList.remove(
                                "drag-active"
                            );

                        }
                    );

                }
            );


            dropZone.addEventListener(
                "drop",
                (event) => {

                    const droppedFiles =
                        event.dataTransfer
                            ?.files;


                    if (
                        !droppedFiles
                        ||
                        droppedFiles.length
                        ===
                        0
                    ) {

                        return;

                    }


                    const files =
                        Array.from(
                            droppedFiles
                        );


                    if (
                        !multipleUploadsAllowed
                        &&
                        files.length > 1
                    ) {

                        showToast(
                            "Multiple file uploads are disabled. Drop one file at a time."
                        );

                        return;

                    }


                    try {

                        const transfer =
                            new DataTransfer();


                        files.forEach(
                            (selectedFile) => {

                                transfer.items.add(
                                    selectedFile
                                );

                            }
                        );


                        fileInput.files =
                            transfer.files;


                        renderSelectedFiles();


                        const validation =
                            getUploadValidation(
                                files
                            );


                        if (
                            !validation.valid
                            &&
                            validation.message
                        ) {

                            showToast(
                                validation.message
                            );

                        }

                    } catch (error) {

                        console.warn(
                            "Drag-and-drop file assignment failed:",
                            error
                        );


                        showToast(
                            "Use Choose files on this browser."
                        );

                    }

                }
            );

        }


        /* =====================================================
           UPLOAD SUBMISSION
           ===================================================== */

        if (uploadForm) {

            uploadForm.addEventListener(
                "submit",
                (event) => {

                    if (
                        !fileInput
                        ||
                        fileInput.files.length
                        ===
                        0
                    ) {

                        event.preventDefault();


                        showToast(
                            "Choose at least one file."
                        );


                        return;

                    }


                    const selectedFiles =
                        Array.from(
                            fileInput.files
                        );


                    const validation =
                        getUploadValidation(
                            selectedFiles
                        );


                    if (
                        !validation.valid
                    ) {

                        event.preventDefault();


                        showToast(
                            validation.message
                            ||
                            "One or more files cannot be uploaded."
                        );


                        renderSelectedFiles();

                        return;

                    }


                    if (uploadSubmitButton) {

                        uploadSubmitButton.disabled =
                            true;


                        uploadSubmitButton.textContent =
                            "Uploading...";

                    }


                    if (cancelUploadButton) {

                        cancelUploadButton.disabled =
                            true;

                    }


                    if (closeUploadButton) {

                        closeUploadButton.disabled =
                            true;

                    }

                }
            );

        }


        /* =====================================================
           TRASH
           ===================================================== */

        const trashForms =
            document.querySelectorAll(
                ".trash-form"
            );


        trashForms.forEach(
            (form) => {

                form.addEventListener(
                    "submit",
                    async (event) => {

                        event.preventDefault();


                        const confirmed =
                            window.confirm(
                                "Move this file to Trash?"
                            );


                        if (!confirmed) {

                            return;

                        }


                        const submitButton =
                            form.querySelector(
                                "button[type='submit']"
                            );


                        if (submitButton) {

                            submitButton.disabled =
                                true;


                            submitButton.textContent =
                                "Moving...";

                        }


                        try {

                            const formData =
                                new FormData(
                                    form
                                );


                            const response =
                                await fetch(
                                    form.action,
                                    {
                                        method:
                                            "POST",

                                        body:
                                            formData,

                                        credentials:
                                            "same-origin",

                                        headers: {
                                            "X-Requested-With":
                                                "XMLHttpRequest",
                                        },
                                    }
                                );


                            if (!response.ok) {

                                let message =
                                    "Could not move file to Trash.";


                                try {

                                    const data =
                                        await response.json();


                                    if (data.detail) {

                                        message =
                                            data.detail;

                                    }

                                } catch {

                                    /*
                                     * Response was not JSON.
                                     */

                                }


                                throw new Error(
                                    message
                                );

                            }


                            showToast(
                                "File moved to Trash."
                            );


                            window.setTimeout(
                                () => {

                                    window.location.reload();

                                },
                                450
                            );

                        } catch (error) {

                            console.error(
                                error
                            );


                            showToast(
                                error.message
                                ||
                                "Could not move file to Trash."
                            );


                            if (submitButton) {

                                submitButton.disabled =
                                    false;


                                submitButton.textContent =
                                    "Move to Trash";

                            }

                        }

                    }
                );

            }
        );


        /* =====================================================
           LOCAL UPLOAD TIMES
           ===================================================== */

        const uploadTimes =
            document.querySelectorAll(
                ".local-upload-time"
            );


        uploadTimes.forEach(
            (element) => {

                const timestamp =
                    element.getAttribute(
                        "datetime"
                    );


                if (!timestamp) {

                    return;

                }


                const date =
                    new Date(
                        timestamp
                    );


                if (
                    Number.isNaN(
                        date.getTime()
                    )
                ) {

                    return;

                }


                element.textContent =
                    date.toLocaleString(
                        undefined,
                        {
                            dateStyle:
                                "medium",

                            timeStyle:
                                "short",
                        }
                    );

            }
        );


        /* =====================================================
           GLOBAL CLICK HANDLING
           ===================================================== */

        document.addEventListener(
            "click",
            (event) => {

                const clickedInsideAccount =
                    event.target.closest(
                        ".account-menu"
                    );


                if (
                    !clickedInsideAccount
                ) {

                    closeAccountDropdown();

                }


                const clickedInsideFileMenu =
                    event.target.closest(
                        ".file-menu-wrap"
                    );


                if (
                    !clickedInsideFileMenu
                ) {

                    closeAllFileMenus();

                }


                const clickedInsideSearch =
                    event.target.closest(
                        ".search-wrap"
                    );


                if (
                    !clickedInsideSearch
                ) {

                    closeSearchSuggestions();

                }

            }
        );


        /* =====================================================
           ESCAPE KEY
           ===================================================== */

        document.addEventListener(
            "keydown",
            (event) => {

                if (
                    event.key
                    !==
                    "Escape"
                ) {

                    return;

                }


                closeAccountDropdown();

                closeAllFileMenus();

                closeSearchSuggestions();


                if (
                    renameModal
                    &&
                    !renameModal.hidden
                ) {

                    closeRenameModal();

                    return;

                }


                if (
                    uploadModal
                    &&
                    !uploadModal.hidden
                ) {

                    closeUploadModal();

                }

            }
        );


        /* =====================================================
           DEFAULT LIBRARY VIEW
           ===================================================== */

        const initialCategory =
            defaultView
            ===
            "recent"

                ? "all"

                : defaultView;


        const initialCategoryButton =
            categoryButtons.find(
                (button) => {

                    return (
                        button.dataset.category
                        ===
                        initialCategory
                    );

                }
            );


        if (initialCategoryButton) {

            activeCategory =
                initialCategory;


            categoryButtons.forEach(
                (button) => {

                    button.classList.toggle(
                        "active",
                        button
                        ===
                        initialCategoryButton
                    );

                }
            );

        }


        /* =====================================================
           INITIAL UPLOAD STATE
           ===================================================== */

        if (uploadSubmitButton) {

            uploadSubmitButton.disabled =
                !fileInput
                ||
                fileInput.files.length
                ===
                0;

        }


        /* =====================================================
           INITIAL FILTER
           ===================================================== */

        applyFilters();


        /* =====================================================
           QUERY PARAMETER MESSAGES
           ===================================================== */

        const query =
            new URLSearchParams(
                window.location.search
            );


        let queryChanged =
            false;


        if (
            query.has(
                "renamed"
            )
        ) {

            showToast(
                "File renamed."
            );


            query.delete(
                "renamed"
            );


            queryChanged =
                true;

        }


        if (
            query.has(
                "uploaded"
            )
        ) {

            showToast(
                "Upload complete."
            );


            query.delete(
                "uploaded"
            );


            queryChanged =
                true;

        }


        if (
            queryChanged
        ) {

            const cleanQuery =
                query.toString();


            window.history.replaceState(
                {},
                "",
                `${
                    window.location.pathname
                }${
                    cleanQuery
                        ? `?${cleanQuery}`
                        : ""
                }${
                    window.location.hash
                }`
            );

        }

    }
);