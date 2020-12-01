angular.module('templates-main', []).run(['$templateCache', function($templateCache) {
	$templateCache.put('app/client/templates/client.html',
	"<!--\n" +
	"   Copyright (C) 2014 Glyptodon LLC\n" +
	"\n" +
	"   Permission is hereby granted, free of charge, to any person obtaining a copy\n" +
	"   of this software and associated documentation files (the \"Software\"), to deal\n" +
	"   in the Software without restriction, including without limitation the rights\n" +
	"   to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n" +
	"   copies of the Software, and to permit persons to whom the Software is\n" +
	"   furnished to do so, subject to the following conditions:\n" +
	"\n" +
	"   The above copyright notice and this permission notice shall be included in\n" +
	"   all copies or substantial portions of the Software.\n" +
	"\n" +
	"   THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n" +
	"   IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n" +
	"   FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n" +
	"   AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n" +
	"   LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n" +
	"   OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n" +
	"   THE SOFTWARE.\n" +
	"-->\n" +
	"\n" +
	"<guac-viewport>\n" +
	"\n" +
	"    <!-- Client view -->\n" +
	"    <div class=\"client-view\">\n" +
	"        <div class=\"client-view-content\">\n" +
	"\n" +
	"            <!-- Central portion of view -->\n" +
	"            <div class=\"client-body\" guac-touch-drag=\"clientDrag\" guac-touch-pinch=\"clientPinch\">\n" +
	"\n" +
	"                <!-- Client -->\n" +
	"                <guac-client client=\"client\"></guac-client>\n" +
	"\n" +
	"            </div>\n" +
	"\n" +
	"            <!-- Bottom portion of view -->\n" +
	"            <div class=\"client-bottom\">\n" +
	"\n" +
	"                <!-- Text input -->\n" +
	"                <div class=\"text-input-container\" ng-show=\"showTextInput\">\n" +
	"                    <guac-text-input needs-focus=\"showTextInput\"></guac-text-input>\n" +
	"                </div>\n" +
	"\n" +
	"                <!-- On-screen keyboard -->\n" +
	"                <div class=\"keyboard-container\" ng-show=\"showOSK\">\n" +
	"                    <guac-osk layout=\"'CLIENT.URL_OSK_LAYOUT' | translate\"></guac-osk>\n" +
	"                </div>\n" +
	"\n" +
	"            </div>\n" +
	"\n" +
	"        </div>\n" +
	"    </div>\n" +
	"\n" +
	"    <!-- File transfers -->\n" +
	"    <div id=\"file-transfer-dialog\" ng-show=\"hasTransfers()\">\n" +
	"        <guac-file-transfer-manager client=\"client\"></guac-file-transfer-manager>\n" +
	"    </div>\n" +
	"\n" +
	"    <!-- Menu -->\n" +
	"    <div class=\"menu\" ng-class=\"{open: menu.shown}\" id=\"guac-menu\">\n" +
	"        <div class=\"menu-content\">\n" +
	"\n" +
	"            <!-- Stationary header -->\n" +
	"            <div class=\"header\">\n" +
	"                <h2>{{client.name}}</h2>\n" +
	"                <guac-user-menu local-actions=\"clientMenuActions\"></guac-user-menu>\n" +
	"            </div>\n" +
	"\n" +
	"            <!-- Scrollable body -->\n" +
	"            <div class=\"menu-body\" guac-touch-drag=\"menuDrag\" guac-scroll=\"menu.scrollState\">\n" +
	"\n" +
	"                <!-- Clipboard -->\n" +
	"                <div class=\"menu-section\" id=\"clipboard-settings\">\n" +
	"                    <h3>{{'CLIENT.SECTION_HEADER_CLIPBOARD' | translate}}</h3>\n" +
	"                    <div class=\"content\">\n" +
	"                        <p class=\"description\">{{'CLIENT.HELP_CLIPBOARD' | translate}}</p>\n" +
	"                        <textarea ng-model=\"client.clipboardData\" rows=\"10\" cols=\"40\" id=\"clipboard\"></textarea>\n" +
	"                    </div>\n" +
	"                </div>\n" +
	"\n" +
	"                <!-- Devices -->\n" +
	"                <div class=\"menu-section\" id=\"devices\" ng-show=\"client.filesystems.length\">\n" +
	"                    <h3>{{'CLIENT.SECTION_HEADER_DEVICES' | translate}}</h3>\n" +
	"                    <div class=\"content\">\n" +
	"                        <div class=\"device filesystem\" ng-repeat=\"filesystem in client.filesystems\" ng-click=\"showFilesystemMenu(filesystem)\">\n" +
	"                            {{filesystem.name}}\n" +
	"                        </div>\n" +
	"                    </div>\n" +
	"                </div>\n" +
	"\n" +
	"                <!-- Input method -->\n" +
	"                <div class=\"menu-section\" id=\"keyboard-settings\">\n" +
	"                    <h3>{{'CLIENT.SECTION_HEADER_INPUT_METHOD' | translate}}</h3>\n" +
	"                    <div class=\"content\">\n" +
	"\n" +
	"                        <!-- No IME -->\n" +
	"                        <div class=\"choice\">\n" +
	"                            <label><input id=\"ime-none\" name=\"input-method\" ng-change=\"closeMenu()\" ng-model=\"menu.inputMethod\" type=\"radio\" value=\"none\"/> {{'CLIENT.NAME_INPUT_METHOD_NONE' | translate}}</label>\n" +
	"                            <p class=\"caption\"><label for=\"ime-none\">{{'CLIENT.HELP_INPUT_METHOD_NONE' | translate}}</label></p>\n" +
	"                        </div>\n" +
	"\n" +
	"                        <!-- Text input -->\n" +
	"                        <div class=\"choice\">\n" +
	"                            <div class=\"figure\"><label for=\"ime-text\"><img src=\"images/settings/tablet-keys.png\" alt=\"\"/></label></div>\n" +
	"                            <label><input id=\"ime-text\" name=\"input-method\" ng-change=\"closeMenu()\" ng-model=\"menu.inputMethod\" type=\"radio\" value=\"text\"/> {{'CLIENT.NAME_INPUT_METHOD_TEXT' | translate}}</label>\n" +
	"                            <p class=\"caption\"><label for=\"ime-text\">{{'CLIENT.HELP_INPUT_METHOD_TEXT' | translate}} </label></p>\n" +
	"                        </div>\n" +
	"\n" +
	"                        <!-- Guac OSK -->\n" +
	"                        <div class=\"choice\">\n" +
	"                            <label><input id=\"ime-osk\" name=\"input-method\" ng-change=\"closeMenu()\" ng-model=\"menu.inputMethod\" type=\"radio\" value=\"osk\"/> {{'CLIENT.NAME_INPUT_METHOD_OSK' | translate}}</label>\n" +
	"                            <p class=\"caption\"><label for=\"ime-osk\">{{'CLIENT.HELP_INPUT_METHOD_OSK' | translate}}</label></p>\n" +
	"                        </div>\n" +
	"\n" +
	"                    </div>\n" +
	"                </div>\n" +
	"\n" +
	"                <!-- Mouse mode -->\n" +
	"                <div class=\"menu-section\" id=\"mouse-settings\">\n" +
	"                    <h3>{{'CLIENT.SECTION_HEADER_MOUSE_MODE' | translate}}</h3>\n" +
	"                    <div class=\"content\">\n" +
	"                        <p class=\"description\">{{'CLIENT.HELP_MOUSE_MODE' | translate}}</p>\n" +
	"\n" +
	"                        <!-- Touchscreen -->\n" +
	"                        <div class=\"choice\">\n" +
	"                            <input name=\"mouse-mode\" ng-change=\"closeMenu()\" ng-model=\"client.clientProperties.emulateAbsoluteMouse\" type=\"radio\" ng-value=\"true\" checked=\"checked\" id=\"absolute\"/>\n" +
	"                            <div class=\"figure\">\n" +
	"                                <label for=\"absolute\"><img src=\"images/settings/touchscreen.png\" alt=\"{{'CLIENT.NAME_MOUSE_MODE_ABSOLUTE' | translate}}\"/></label>\n" +
	"                                <p class=\"caption\"><label for=\"absolute\">{{'CLIENT.HELP_MOUSE_MODE_ABSOLUTE' | translate}}</label></p>\n" +
	"                            </div>\n" +
	"                        </div>\n" +
	"\n" +
	"                        <!-- Touchpad -->\n" +
	"                        <div class=\"choice\">\n" +
	"                            <input name=\"mouse-mode\" ng-change=\"closeMenu()\" ng-model=\"client.clientProperties.emulateAbsoluteMouse\" type=\"radio\" ng-value=\"false\" id=\"relative\"/>\n" +
	"                            <div class=\"figure\">\n" +
	"                                <label for=\"relative\"><img src=\"images/settings/touchpad.png\" alt=\"{{'CLIENT.NAME_MOUSE_MODE_RELATIVE' | translate}}\"/></label>\n" +
	"                                <p class=\"caption\"><label for=\"relative\">{{'CLIENT.HELP_MOUSE_MODE_RELATIVE' | translate}}</label></p>\n" +
	"                            </div>\n" +
	"                        </div>\n" +
	"\n" +
	"                    </div>\n" +
	"                </div>\n" +
	"\n" +
	"                <!-- Display options -->\n" +
	"                <div class=\"menu-section\" id=\"display-settings\">\n" +
	"                    <h3>{{'CLIENT.SECTION_HEADER_DISPLAY' | translate}}</h3>\n" +
	"                    <div class=\"content\">\n" +
	"                        <div id=\"zoom-settings\">\n" +
	"                            <div ng-click=\"zoomOut()\" id=\"zoom-out\"><img src=\"images/settings/zoom-out.png\" alt=\"-\"/></div>\n" +
	"                            <div id=\"zoom-state\">{{formattedScale()}}%</div>\n" +
	"                            <div ng-click=\"zoomIn()\" id=\"zoom-in\"><img src=\"images/settings/zoom-in.png\" alt=\"+\"/></div>\n" +
	"                        </div>\n" +
	"                        <div><label><input ng-model=\"menu.autoFit\" ng-change=\"changeAutoFit()\" ng-disabled=\"autoFitDisabled()\" type=\"checkbox\" id=\"auto-fit\"/> {{'CLIENT.TEXT_ZOOM_AUTO_FIT' | translate}}</label></div>\n" +
	"                    </div>\n" +
	"                </div>\n" +
	"\n" +
	"            </div>\n" +
	"\n" +
	"        </div>\n" +
	"    </div>\n" +
	"\n" +
	"    <!-- Filesystem menu -->\n" +
	"    <div id=\"filesystem-menu\" class=\"menu\" ng-class=\"{open: isFilesystemMenuShown()}\">\n" +
	"        <div class=\"menu-content\">\n" +
	"\n" +
	"            <!-- Stationary header -->\n" +
	"            <div class=\"header\">\n" +
	"                <h2>{{filesystemMenuContents.name}}</h2>\n" +
	"                <button class=\"upload button\" guac-upload=\"uploadFiles\">{{'CLIENT.ACTION_UPLOAD_FILES' | translate}}</button>\n" +
	"                <button class=\"back\" ng-click=\"hideFilesystemMenu()\">{{'CLIENT.ACTION_NAVIGATE_BACK' | translate}}</button>\n" +
	"            </div>\n" +
	"\n" +
	"            <!-- Breadcrumbs -->\n" +
	"            <div class=\"header breadcrumbs\"><div\n" +
	"                    class=\"breadcrumb root\"\n" +
	"                    ng-click=\"changeDirectory(filesystemMenuContents, filesystemMenuContents.root)\"></div><div\n" +
	"                        class=\"breadcrumb\"\n" +
	"                        ng-repeat=\"file in getPath(filesystemMenuContents.currentDirectory)\"\n" +
	"                        ng-click=\"changeDirectory(filesystemMenuContents, file)\">{{file.name}}</div>\n" +
	"            </div>\n" +
	"\n" +
	"            <!-- Scrollable body -->\n" +
	"            <div class=\"menu-body\">\n" +
	"                <guac-file-browser client=\"client\" filesystem=\"filesystemMenuContents\"></guac-file-browser>\n" +
	"            </div>\n" +
	"\n" +
	"        </div>\n" +
	"    </div>\n" +
	"\n" +
	"</guac-viewport>");
	$templateCache.put('app/client/templates/file.html',
	"<div class=\"list-item\">\n" +
	"    <!--\n" +
	"       Copyright (C) 2015 Glyptodon LLC\n" +
	"\n" +
	"       Permission is hereby granted, free of charge, to any person obtaining a copy\n" +
	"       of this software and associated documentation files (the \"Software\"), to deal\n" +
	"       in the Software without restriction, including without limitation the rights\n" +
	"       to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n" +
	"       copies of the Software, and to permit persons to whom the Software is\n" +
	"       furnished to do so, subject to the following conditions:\n" +
	"\n" +
	"       The above copyright notice and this permission notice shall be included in\n" +
	"       all copies or substantial portions of the Software.\n" +
	"\n" +
	"       THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n" +
	"       IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n" +
	"       FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n" +
	"       AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n" +
	"       LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n" +
	"       OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n" +
	"       THE SOFTWARE.\n" +
	"    -->\n" +
	"\n" +
	"    <!-- Filename and icon -->\n" +
	"    <div class=\"caption\">\n" +
	"        <div class=\"icon\"></div>\n" +
	"        {{::name}}\n" +
	"    </div>\n" +
	"\n" +
	"</div>");
	$templateCache.put('app/client/templates/guacClient.html',
	"<div class=\"main\" guac-resize=\"mainElementResized\">\n" +
	"    <!--\n" +
	"       Copyright (C) 2014 Glyptodon LLC\n" +
	"\n" +
	"       Permission is hereby granted, free of charge, to any person obtaining a copy\n" +
	"       of this software and associated documentation files (the \"Software\"), to deal\n" +
	"       in the Software without restriction, including without limitation the rights\n" +
	"       to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n" +
	"       copies of the Software, and to permit persons to whom the Software is\n" +
	"       furnished to do so, subject to the following conditions:\n" +
	"\n" +
	"       The above copyright notice and this permission notice shall be included in\n" +
	"       all copies or substantial portions of the Software.\n" +
	"\n" +
	"       THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n" +
	"       IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n" +
	"       FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n" +
	"       AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n" +
	"       LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n" +
	"       OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n" +
	"       THE SOFTWARE.\n" +
	"    -->\n" +
	"\n" +
	"    <!-- Display -->\n" +
	"    <div class=\"displayOuter\">\n" +
	"\n" +
	"        <div class=\"displayMiddle\">\n" +
	"            <div class=\"display software-cursor\">\n" +
	"            </div>\n" +
	"        </div>\n" +
	"\n" +
	"    </div>\n" +
	"\n" +
	"</div>");
	$templateCache.put('app/client/templates/guacFileBrowser.html',
	"<div class=\"file-browser\">\n" +
	"    <!--\n" +
	"       Copyright (C) 2015 Glyptodon LLC\n" +
	"\n" +
	"       Permission is hereby granted, free of charge, to any person obtaining a copy\n" +
	"       of this software and associated documentation files (the \"Software\"), to deal\n" +
	"       in the Software without restriction, including without limitation the rights\n" +
	"       to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n" +
	"       copies of the Software, and to permit persons to whom the Software is\n" +
	"       furnished to do so, subject to the following conditions:\n" +
	"\n" +
	"       The above copyright notice and this permission notice shall be included in\n" +
	"       all copies or substantial portions of the Software.\n" +
	"\n" +
	"       THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n" +
	"       IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n" +
	"       FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n" +
	"       AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n" +
	"       LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n" +
	"       OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n" +
	"       THE SOFTWARE.\n" +
	"    -->\n" +
	"\n" +
	"    <!-- Current directory contents -->\n" +
	"    <div class=\"current-directory-contents\"></div>\n" +
	"\n" +
	"</div>");
	$templateCache.put('app/client/templates/guacFileTransfer.html',
	"<div class=\"transfer\" ng-class=\"{'in-progress': isInProgress(), 'savable': isSavable(), 'error': hasError()}\" ng-click=\"save()\">\n" +
	"    <!--\n" +
	"       Copyright (C) 2014 Glyptodon LLC\n" +
	"\n" +
	"       Permission is hereby granted, free of charge, to any person obtaining a copy\n" +
	"       of this software and associated documentation files (the \"Software\"), to deal\n" +
	"       in the Software without restriction, including without limitation the rights\n" +
	"       to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n" +
	"       copies of the Software, and to permit persons to whom the Software is\n" +
	"       furnished to do so, subject to the following conditions:\n" +
	"\n" +
	"       The above copyright notice and this permission notice shall be included in\n" +
	"       all copies or substantial portions of the Software.\n" +
	"\n" +
	"       THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n" +
	"       IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n" +
	"       FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n" +
	"       AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n" +
	"       LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n" +
	"       OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n" +
	"       THE SOFTWARE.\n" +
	"    -->\n" +
	"\n" +
	"    <!-- Overall status of transfer -->\n" +
	"    <div class=\"transfer-status\">\n" +
	"\n" +
	"        <!-- Filename and progress bar -->\n" +
	"        <div class=\"filename\">\n" +
	"            <div class=\"progress\"><div ng-style=\"{'width': getPercentDone() + '%'}\" class=\"bar\"></div></div>\n" +
	"            {{transfer.filename}}\n" +
	"        </div>\n" +
	"\n" +
	"        <!-- Error text -->\n" +
	"        <p class=\"error-text\">{{getErrorText() | translate}}</p>\n" +
	"\n" +
	"    </div>\n" +
	"\n" +
	"    <!-- Progress/status text -->\n" +
	"    <div class=\"text\"\n" +
	"         translate=\"CLIENT.TEXT_FILE_TRANSFER_PROGRESS\"\n" +
	"         translate-values=\"{PROGRESS: getProgressValue(), UNIT: getProgressUnit()}\"></div>\n" +
	"\n" +
	"</div>");
	$templateCache.put('app/client/templates/guacFileTransferManager.html',
	"<div class=\"transfer-manager\">\n" +
	"    <!--\n" +
	"       Copyright (C) 2014 Glyptodon LLC\n" +
	"\n" +
	"       Permission is hereby granted, free of charge, to any person obtaining a copy\n" +
	"       of this software and associated documentation files (the \"Software\"), to deal\n" +
	"       in the Software without restriction, including without limitation the rights\n" +
	"       to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n" +
	"       copies of the Software, and to permit persons to whom the Software is\n" +
	"       furnished to do so, subject to the following conditions:\n" +
	"\n" +
	"       The above copyright notice and this permission notice shall be included in\n" +
	"       all copies or substantial portions of the Software.\n" +
	"\n" +
	"       THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n" +
	"       IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n" +
	"       FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n" +
	"       AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n" +
	"       LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n" +
	"       OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n" +
	"       THE SOFTWARE.\n" +
	"    -->\n" +
	"\n" +
	"    <!-- File transfer manager header -->\n" +
	"    <div class=\"header\">\n" +
	"        <h2>{{'CLIENT.SECTION_HEADER_FILE_TRANSFERS' | translate}}</h2>\n" +
	"        <button ng-click=\"clearCompletedTransfers()\">{{'CLIENT.ACTION_CLEAR_COMPLETED_TRANSFERS' | translate}}</button>\n" +
	"    </div>\n" +
	"\n" +
	"    <!-- Sent/received files -->\n" +
	"    <div class=\"transfer-manager-body\">\n" +
	"        <div class=\"transfers\">\n" +
	"            <guac-file-transfer\n" +
	"                transfer=\"upload\"\n" +
	"                ng-repeat=\"upload in client.uploads\">\n" +
	"            </guac-file-transfer><guac-file-transfer\n" +
	"                transfer=\"download\"\n" +
	"                ng-repeat=\"download in client.downloads\">\n" +
	"            </guac-file-transfer>\n" +
	"        </div>\n" +
	"    </div>\n" +
	"\n" +
	"</div>");
	$templateCache.put('app/client/templates/guacThumbnail.html',
	"<div class=\"thumbnail-main\" guac-resize=\"updateDisplayScale\">\n" +
	"    <!--\n" +
	"       Copyright (C) 2014 Glyptodon LLC\n" +
	"\n" +
	"       Permission is hereby granted, free of charge, to any person obtaining a copy\n" +
	"       of this software and associated documentation files (the \"Software\"), to deal\n" +
	"       in the Software without restriction, including without limitation the rights\n" +
	"       to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n" +
	"       copies of the Software, and to permit persons to whom the Software is\n" +
	"       furnished to do so, subject to the following conditions:\n" +
	"\n" +
	"       The above copyright notice and this permission notice shall be included in\n" +
	"       all copies or substantial portions of the Software.\n" +
	"\n" +
	"       THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n" +
	"       IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n" +
	"       FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n" +
	"       AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n" +
	"       LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n" +
	"       OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n" +
	"       THE SOFTWARE.\n" +
	"    -->\n" +
	"\n" +
	"    <!-- Display -->\n" +
	"    <div class=\"display\">\n" +
	"    </div>\n" +
	"\n" +
	"    <!-- Dummy background thumbnail -->\n" +
	"    <img alt=\"\" ng-src=\"{{thumbnail}}\"/>\n" +
	"\n" +
	"</div>");
	$templateCache.put('app/client/templates/guacViewport.html',
	"<div class=\"viewport\" ng-transclude>\n" +
	"    <!--\n" +
	"       Copyright (C) 2014 Glyptodon LLC\n" +
	"\n" +
	"       Permission is hereby granted, free of charge, to any person obtaining a copy\n" +
	"       of this software and associated documentation files (the \"Software\"), to deal\n" +
	"       in the Software without restriction, including without limitation the rights\n" +
	"       to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n" +
	"       copies of the Software, and to permit persons to whom the Software is\n" +
	"       furnished to do so, subject to the following conditions:\n" +
	"\n" +
	"       The above copyright notice and this permission notice shall be included in\n" +
	"       all copies or substantial portions of the Software.\n" +
	"\n" +
	"       THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n" +
	"       IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n" +
	"       FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n" +
	"       AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n" +
	"       LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n" +
	"       OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n" +
	"       THE SOFTWARE.\n" +
	"    -->\n" +
	"</div>");
	$templateCache.put('app/element/templates/blank.html',
	"<!DOCTYPE html>\n" +
	"<html>\n" +
	"    <head>\n" +
	"        <meta http-equiv=\"Content-Type\" content=\"text/html; charset=UTF-8\">\n" +
	"        <title>_</title>\n" +
	"    </head>\n" +
	"    <!--\n" +
	"       Copyright (C) 2015 Glyptodon LLC\n" +
	"\n" +
	"       Permission is hereby granted, free of charge, to any person obtaining a copy\n" +
	"       of this software and associated documentation files (the \"Software\"), to deal\n" +
	"       in the Software without restriction, including without limitation the rights\n" +
	"       to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n" +
	"       copies of the Software, and to permit persons to whom the Software is\n" +
	"       furnished to do so, subject to the following conditions:\n" +
	"\n" +
	"       The above copyright notice and this permission notice shall be included in\n" +
	"       all copies or substantial portions of the Software.\n" +
	"\n" +
	"       THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n" +
	"       IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n" +
	"       FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n" +
	"       AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n" +
	"       LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n" +
	"       OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n" +
	"       THE SOFTWARE.\n" +
	"    -->\n" +
	"    <body></body>\n" +
	"</html>");
	$templateCache.put('app/form/templates/checkboxField.html',
	"<input type=\"checkbox\" ng-model=\"typedValue\" autocorrect=\"off\" autocapitalize=\"off\"/>");
	$templateCache.put('app/form/templates/dateField.html',
	"<div class=\"date-field\">\n" +
	"    <input type=\"date\"\n" +
	"           ng-model=\"typedValue\"\n" +
	"           ng-model-options=\"modelOptions\"\n" +
	"           guac-lenient-date\n" +
	"           placeholder=\"{{'FORM.FIELD_PLACEHOLDER_DATE' | translate}}\"\n" +
	"           autocorrect=\"off\"\n" +
	"           autocapitalize=\"off\"/>\n" +
	"</div>");
	$templateCache.put('app/form/templates/form.html',
	"<div class=\"form-group\">\n" +
	"    <div ng-repeat=\"form in forms\" class=\"form\">\n" +
	"        <!--\n" +
	"            Copyright 2015 Glyptodon LLC.\n" +
	"\n" +
	"            Permission is hereby granted, free of charge, to any person obtaining a copy\n" +
	"            of this software and associated documentation files (the \"Software\"), to deal\n" +
	"            in the Software without restriction, including without limitation the rights\n" +
	"            to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n" +
	"            copies of the Software, and to permit persons to whom the Software is\n" +
	"            furnished to do so, subject to the following conditions:\n" +
	"\n" +
	"            The above copyright notice and this permission notice shall be included in\n" +
	"            all copies or substantial portions of the Software.\n" +
	"\n" +
	"            THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n" +
	"            IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n" +
	"            FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n" +
	"            AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n" +
	"            LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n" +
	"            OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n" +
	"            THE SOFTWARE.\n" +
	"        -->\n" +
	"\n" +
	"        <!-- Form name -->\n" +
	"        <h3 ng-show=\"form.name\">{{getSectionHeader(form) | translate}}</h3>\n" +
	"\n" +
	"        <!-- All fields in form -->\n" +
	"        <div class=\"fields\">\n" +
	"            <guac-form-field ng-repeat=\"field in form.fields\" namespace=\"namespace\"\n" +
	"                             field=\"field\" model=\"values[field.name]\"></guac-form-field>\n" +
	"        </div>\n" +
	"\n" +
	"    </div>\n" +
	"</div>");
	$templateCache.put('app/form/templates/formField.html',
	"<label class=\"labeled-field\" ng-class=\"{empty: !model}\">\n" +
	"    <!--\n" +
	"        Copyright 2014 Glyptodon LLC.\n" +
	"\n" +
	"        Permission is hereby granted, free of charge, to any person obtaining a copy\n" +
	"        of this software and associated documentation files (the \"Software\"), to deal\n" +
	"        in the Software without restriction, including without limitation the rights\n" +
	"        to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n" +
	"        copies of the Software, and to permit persons to whom the Software is\n" +
	"        furnished to do so, subject to the following conditions:\n" +
	"\n" +
	"        The above copyright notice and this permission notice shall be included in\n" +
	"        all copies or substantial portions of the Software.\n" +
	"\n" +
	"        THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n" +
	"        IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n" +
	"        FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n" +
	"        AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n" +
	"        LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n" +
	"        OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n" +
	"        THE SOFTWARE.\n" +
	"    -->\n" +
	"\n" +
	"    <!-- Field header -->\n" +
	"    <span class=\"field-header\">{{getFieldHeader() | translate}}</span>\n" +
	"\n" +
	"    <!-- Field content -->\n" +
	"    <div class=\"form-field\">\n" +
	"    </div>\n" +
	"\n" +
	"</label>");
	$templateCache.put('app/form/templates/numberField.html',
	"<input type=\"number\" ng-model=\"typedValue\" autocorrect=\"off\" autocapitalize=\"off\"/>");
	$templateCache.put('app/form/templates/passwordField.html',
	"<div class=\"password-field\">\n" +
	"    <input type=\"{{passwordInputType}}\" ng-model=\"model\" ng-trim=\"false\" autocorrect=\"off\" autocapitalize=\"off\"/>\n" +
	"    <div class=\"icon toggle-password\" ng-click=\"togglePassword()\" title=\"{{getTogglePasswordHelpText() | translate}}\"></div>\n" +
	"</div>");
	$templateCache.put('app/form/templates/selectField.html',
	"<select ng-model=\"model\" ng-options=\"option as getFieldOption(option) | translate for option in field.options | orderBy: value\"></select>");
	$templateCache.put('app/form/templates/textAreaField.html',
	"<textarea ng-model=\"model\" autocorrect=\"off\" autocapitalize=\"off\"></textarea>");
	$templateCache.put('app/form/templates/textField.html',
	"<input type=\"text\" ng-model=\"model\" autocorrect=\"off\" autocapitalize=\"off\"/>");
	$templateCache.put('app/form/templates/timeField.html',
	"<div class=\"time-field\">\n" +
	"    <input type=\"time\"\n" +
	"           ng-model=\"typedValue\"\n" +
	"           ng-model-options=\"modelOptions\"\n" +
	"           guac-lenient-time\n" +
	"           placeholder=\"{{'FORM.FIELD_PLACEHOLDER_TIME' | translate}}\"\n" +
	"           autocorrect=\"off\"\n" +
	"           autocapitalize=\"off\"/>\n" +
	"</div>");
	$templateCache.put('app/form/templates/timeZoneField.html',
	"<div class=\"time-zone-field\">\n" +
	"\n" +
	"    <!-- Available time zone regions -->\n" +
	"    <select class=\"time-zone-region\"\n" +
	"            ng-model=\"region\"\n" +
	"            ng-options=\"name for name in regions | orderBy: name\"></select>\n" +
	"\n" +
	"    <!-- Time zones within selected region -->\n" +
	"    <select class=\"time-zone\"\n" +
	"            ng-disabled=\"!region\"\n" +
	"            ng-model=\"model\"\n" +
	"            ng-options=\"name for (name, value) in timeZones[region] | orderBy: name\"></select>\n" +
	"\n" +
	"</div>");
	$templateCache.put('app/groupList/templates/guacGroupList.html',
	"<div class=\"group-list\">\n" +
	"    <!--\n" +
	"       Copyright (C) 2014 Glyptodon LLC\n" +
	"\n" +
	"       Permission is hereby granted, free of charge, to any person obtaining a copy\n" +
	"       of this software and associated documentation files (the \"Software\"), to deal\n" +
	"       in the Software without restriction, including without limitation the rights\n" +
	"       to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n" +
	"       copies of the Software, and to permit persons to whom the Software is\n" +
	"       furnished to do so, subject to the following conditions:\n" +
	"\n" +
	"       The above copyright notice and this permission notice shall be included in\n" +
	"       all copies or substantial portions of the Software.\n" +
	"\n" +
	"       THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n" +
	"       IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n" +
	"       FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n" +
	"       AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n" +
	"       LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n" +
	"       OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n" +
	"       THE SOFTWARE.\n" +
	"    -->\n" +
	"\n" +
	"    <script type=\"text/ng-template\" id=\"nestedGroup.html\">\n" +
	"\n" +
	"        <!-- Connection -->\n" +
	"        <div class=\"connection\" ng-show=\"isVisibleConnection(item)\">\n" +
	"            <div class=\"caption\">\n" +
	"                <ng-include src=\"connectionTemplate\"/>\n" +
	"            </div>\n" +
	"        </div>\n" +
	"\n" +
	"        <!-- Connection group -->\n" +
	"        <div class=\"group\" ng-show=\"isVisibleConnectionGroup(item)\">\n" +
	"            <div class=\"caption\">\n" +
	"\n" +
	"                <!-- Connection group icon -->\n" +
	"                <div class=\"icon group type\" ng-click=\"toggleExpanded(item)\"\n" +
	"                     ng-class=\"{expanded: item.isExpanded, empty: !item.children.length, balancer: item.isBalancing}\"></div>\n" +
	"\n" +
	"                <ng-include src=\"connectionGroupTemplate\"/>\n" +
	"\n" +
	"            </div>\n" +
	"\n" +
	"            <!-- Children of this group -->\n" +
	"            <div class=\"children\" ng-show=\"item.isExpanded\">\n" +
	"                <div class=\"list-item\" ng-repeat=\"item in item.children | orderBy : 'name'\" ng-include=\"'nestedGroup.html'\">\n" +
	"            </div>\n" +
	"\n" +
	"        </div>\n" +
	"\n" +
	"    </script>\n" +
	"\n" +
	"    <!-- Root-level connections / groups -->\n" +
	"    <div class=\"group-list-page\">\n" +
	"        <div class=\"list-item\" ng-repeat=\"item in childrenPage\" ng-include=\"'nestedGroup.html'\"></div>\n" +
	"    </div>\n" +
	"\n" +
	"    <!-- Pager for connections / groups -->\n" +
	"    <guac-pager page=\"childrenPage\" items=\"rootItems | orderBy : 'name'\"\n" +
	"                page-size=\"pageSize\"></guac-pager>\n" +
	"\n" +
	"</div>");
	$templateCache.put('app/groupList/templates/guacGroupListFilter.html',
	"<div class=\"group-list-filter filter\">\n" +
	"    <!--\n" +
	"       Copyright (C) 2015 Glyptodon LLC\n" +
	"\n" +
	"       Permission is hereby granted, free of charge, to any person obtaining a copy\n" +
	"       of this software and associated documentation files (the \"Software\"), to deal\n" +
	"       in the Software without restriction, including without limitation the rights\n" +
	"       to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n" +
	"       copies of the Software, and to permit persons to whom the Software is\n" +
	"       furnished to do so, subject to the following conditions:\n" +
	"\n" +
	"       The above copyright notice and this permission notice shall be included in\n" +
	"       all copies or substantial portions of the Software.\n" +
	"\n" +
	"       THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n" +
	"       IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n" +
	"       FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n" +
	"       AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n" +
	"       LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n" +
	"       OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n" +
	"       THE SOFTWARE.\n" +
	"    -->\n" +
	"\n" +
	"    <!-- Filter string -->\n" +
	"    <input class=\"search-string\" placeholder=\"{{placeholder()}}\" type=\"text\" ng-model=\"searchString\"/>\n" +
	"\n" +
	"</div>");
	$templateCache.put('app/home/templates/connection.html',
	"<a ng-href=\"#/client/{{context.getClientIdentifier(item)}}\">\n" +
	"    <!--\n" +
	"       Copyright (C) 2014 Glyptodon LLC\n" +
	"\n" +
	"       Permission is hereby granted, free of charge, to any person obtaining a copy\n" +
	"       of this software and associated documentation files (the \"Software\"), to deal\n" +
	"       in the Software without restriction, including without limitation the rights\n" +
	"       to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n" +
	"       copies of the Software, and to permit persons to whom the Software is\n" +
	"       furnished to do so, subject to the following conditions:\n" +
	"\n" +
	"       The above copyright notice and this permission notice shall be included in\n" +
	"       all copies or substantial portions of the Software.\n" +
	"\n" +
	"       THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n" +
	"       IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n" +
	"       FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n" +
	"       AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n" +
	"       LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n" +
	"       OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n" +
	"       THE SOFTWARE.\n" +
	"    -->\n" +
	"\n" +
	"    <div class=\"caption\" ng-class=\"{active: item.getActiveConnections()}\">\n" +
	"\n" +
	"        <!-- Connection icon -->\n" +
	"        <div class=\"protocol\">\n" +
	"            <div class=\"icon type\" ng-class=\"item.protocol\"></div>\n" +
	"        </div>\n" +
	"\n" +
	"        <!-- Connection name -->\n" +
	"        <span class=\"name\">{{item.name}}</span>\n" +
	"        \n" +
	"        <!-- Active user count -->\n" +
	"        <span class=\"activeUserCount\" ng-show=\"item.getActiveConnections()\"\n" +
	"            translate=\"HOME.INFO_ACTIVE_USER_COUNT\"\n" +
	"            translate-values=\"{USERS: item.getActiveConnections()}\"></span>\n" +
	"\n" +
	"    </div>\n" +
	"</a>");
	$templateCache.put('app/home/templates/connectionGroup.html',
	"<span class=\"name\">\n" +
	"    <!--\n" +
	"       Copyright (C) 2014 Glyptodon LLC\n" +
	"\n" +
	"       Permission is hereby granted, free of charge, to any person obtaining a copy\n" +
	"       of this software and associated documentation files (the \"Software\"), to deal\n" +
	"       in the Software without restriction, including without limitation the rights\n" +
	"       to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n" +
	"       copies of the Software, and to permit persons to whom the Software is\n" +
	"       furnished to do so, subject to the following conditions:\n" +
	"\n" +
	"       The above copyright notice and this permission notice shall be included in\n" +
	"       all copies or substantial portions of the Software.\n" +
	"\n" +
	"       THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n" +
	"       IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n" +
	"       FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n" +
	"       AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n" +
	"       LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n" +
	"       OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n" +
	"       THE SOFTWARE.\n" +
	"    -->\n" +
	"\n" +
	"    <a ng-show=\"item.isBalancing\" ng-href=\"#/client/{{context.getClientIdentifier(item)}}\">{{item.name}}</a>\n" +
	"    <span ng-show=\"!item.isBalancing\">{{item.name}}</span>\n" +
	"</span>");
	$templateCache.put('app/home/templates/guacRecentConnections.html',
	"<div>\n" +
	"    <!--\n" +
	"       Copyright (C) 2014 Glyptodon LLC\n" +
	"\n" +
	"       Permission is hereby granted, free of charge, to any person obtaining a copy\n" +
	"       of this software and associated documentation files (the \"Software\"), to deal\n" +
	"       in the Software without restriction, including without limitation the rights\n" +
	"       to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n" +
	"       copies of the Software, and to permit persons to whom the Software is\n" +
	"       furnished to do so, subject to the following conditions:\n" +
	"\n" +
	"       The above copyright notice and this permission notice shall be included in\n" +
	"       all copies or substantial portions of the Software.\n" +
	"\n" +
	"       THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n" +
	"       IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n" +
	"       FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n" +
	"       AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n" +
	"       LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n" +
	"       OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n" +
	"       THE SOFTWARE.\n" +
	"    -->\n" +
	"\n" +
	"    <!-- Text displayed if no recent connections exist -->\n" +
	"    <p class=\"placeholder\" ng-hide=\"hasRecentConnections()\">{{'HOME.INFO_NO_RECENT_CONNECTIONS' | translate}}</p>\n" +
	"\n" +
	"    <!-- All active connections -->\n" +
	"    <div ng-repeat=\"activeConnection in activeConnections\" class=\"connection\">\n" +
	"        <a href=\"#/client/{{activeConnection.client.id}}\">\n" +
	"\n" +
	"            <!-- Connection thumbnail -->\n" +
	"            <div class=\"thumbnail\">\n" +
	"                <guac-thumbnail client=\"activeConnection.client\"></guac-thumbnail>\n" +
	"            </div>\n" +
	"\n" +
	"            <!-- Connection name -->\n" +
	"            <div class=\"caption\">\n" +
	"                <span class=\"name\">{{activeConnection.name}}</span>\n" +
	"            </div>\n" +
	"\n" +
	"        </a>\n" +
	"    </div>\n" +
	"    \n" +
	"    <!-- All recent connections -->\n" +
	"    <div ng-repeat=\"recentConnection in recentConnections\" class=\"connection\">\n" +
	"        <a href=\"#/client/{{recentConnection.entry.id}}\">\n" +
	"\n" +
	"            <!-- Connection thumbnail -->\n" +
	"            <div class=\"thumbnail\">\n" +
	"                <img alt=\"{{recentConnection.name}}\" ng-src=\"{{recentConnection.entry.thumbnail}}\"/>\n" +
	"            </div>\n" +
	"\n" +
	"            <!-- Connection name -->\n" +
	"            <div class=\"caption\">\n" +
	"                <span class=\"name\">{{recentConnection.name}}</span>\n" +
	"            </div>\n" +
	"\n" +
	"        </a>\n" +
	"    </div>\n" +
	"\n" +
	"</div>");
	$templateCache.put('app/home/templates/home.html',
	"<!--\n" +
	"   Copyright (C) 2015 Glyptodon LLC\n" +
	"\n" +
	"   Permission is hereby granted, free of charge, to any person obtaining a copy\n" +
	"   of this software and associated documentation files (the \"Software\"), to deal\n" +
	"   in the Software without restriction, including without limitation the rights\n" +
	"   to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n" +
	"   copies of the Software, and to permit persons to whom the Software is\n" +
	"   furnished to do so, subject to the following conditions:\n" +
	"\n" +
	"   The above copyright notice and this permission notice shall be included in\n" +
	"   all copies or substantial portions of the Software.\n" +
	"\n" +
	"   THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n" +
	"   IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n" +
	"   FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n" +
	"   AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n" +
	"   LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n" +
	"   OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n" +
	"   THE SOFTWARE.\n" +
	"-->\n" +
	"\n" +
	"<div class=\"view\" ng-class=\"{loading: !isLoaded()}\">\n" +
	"\n" +
	"    <div class=\"connection-list-ui\">\n" +
	"\n" +
	"        <!-- The recent connections for this user -->\n" +
	"        <div class=\"header\">\n" +
	"            <h2>{{'HOME.SECTION_HEADER_RECENT_CONNECTIONS' | translate}}</h2>\n" +
	"            <guac-user-menu></guac-user-menu>\n" +
	"        </div>\n" +
	"        <div class=\"recent-connections\">\n" +
	"            <guac-recent-connections root-groups=\"rootConnectionGroups\"></guac-recent-connections>\n" +
	"        </div>\n" +
	"\n" +
	"        <!-- All connections for this user -->\n" +
	"        <div class=\"header\">\n" +
	"            <h2>{{'HOME.SECTION_HEADER_ALL_CONNECTIONS' | translate}}</h2>\n" +
	"            <guac-group-list-filter connection-groups=\"rootConnectionGroups\"\n" +
	"                filtered-connection-groups=\"filteredRootConnectionGroups\"\n" +
	"                placeholder=\"'HOME.FIELD_PLACEHOLDER_FILTER' | translate\"\n" +
	"                connection-properties=\"filteredConnectionProperties\"\n" +
	"                connection-group-properties=\"filteredConnectionGroupProperties\"></guac-group-list-filter>\n" +
	"        </div>\n" +
	"        <div class=\"all-connections\">\n" +
	"            <guac-group-list\n" +
	"                context=\"context\"\n" +
	"                connection-groups=\"filteredRootConnectionGroups\"\n" +
	"                connection-template=\"'app/home/templates/connection.html'\"\n" +
	"                connection-group-template=\"'app/home/templates/connectionGroup.html'\"\n" +
	"                page-size=\"20\"></guac-group-list>\n" +
	"        </div>\n" +
	"\n" +
	"    </div>\n" +
	"\n" +
	"</div>");
	$templateCache.put('app/list/templates/guacFilter.html',
	"<div class=\"filter\">\n" +
	"    <!--\n" +
	"       Copyright (C) 2015 Glyptodon LLC\n" +
	"\n" +
	"       Permission is hereby granted, free of charge, to any person obtaining a copy\n" +
	"       of this software and associated documentation files (the \"Software\"), to deal\n" +
	"       in the Software without restriction, including without limitation the rights\n" +
	"       to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n" +
	"       copies of the Software, and to permit persons to whom the Software is\n" +
	"       furnished to do so, subject to the following conditions:\n" +
	"\n" +
	"       The above copyright notice and this permission notice shall be included in\n" +
	"       all copies or substantial portions of the Software.\n" +
	"\n" +
	"       THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n" +
	"       IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n" +
	"       FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n" +
	"       AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n" +
	"       LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n" +
	"       OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n" +
	"       THE SOFTWARE.\n" +
	"    -->\n" +
	"\n" +
	"    <!-- Filter string -->\n" +
	"    <input class=\"search-string\" placeholder=\"{{placeholder()}}\" type=\"text\" ng-model=\"searchString\"/>\n" +
	"\n" +
	"</div>");
	$templateCache.put('app/list/templates/guacPager.html',
	"<div class=\"pager\" ng-show=\"pageNumbers.length > 1\">\n" +
	"    <!--\n" +
	"       Copyright (C) 2015 Glyptodon LLC\n" +
	"\n" +
	"       Permission is hereby granted, free of charge, to any person obtaining a copy\n" +
	"       of this software and associated documentation files (the \"Software\"), to deal\n" +
	"       in the Software without restriction, including without limitation the rights\n" +
	"       to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n" +
	"       copies of the Software, and to permit persons to whom the Software is\n" +
	"       furnished to do so, subject to the following conditions:\n" +
	"\n" +
	"       The above copyright notice and this permission notice shall be included in\n" +
	"       all copies or substantial portions of the Software.\n" +
	"\n" +
	"       THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n" +
	"       IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n" +
	"       FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n" +
	"       AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n" +
	"       LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n" +
	"       OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n" +
	"       THE SOFTWARE.\n" +
	"    -->\n" +
	"\n" +
	"    <!-- First / Previous -->\n" +
	"    <div class=\"first-page icon\" ng-class=\"{disabled: !canSelectPage(firstPage)}\"    ng-click=\"selectPage(firstPage)\"/>\n" +
	"    <div class=\"prev-page icon\"  ng-class=\"{disabled: !canSelectPage(previousPage)}\" ng-click=\"selectPage(previousPage)\"/>\n" +
	"\n" +
	"    <!-- Indicator of the existence of pages before the first page number shown -->\n" +
	"    <div class=\"more-pages\" ng-show=\"hasMorePagesBefore()\">...</div>\n" +
	"    \n" +
	"    <!-- Page numbers -->\n" +
	"    <ul class=\"page-numbers\">\n" +
	"        <li class=\"set-page\"\n" +
	"            ng-class=\"{current: isSelected(pageNumber)}\"\n" +
	"            ng-repeat=\"pageNumber in pageNumbers\"\n" +
	"            ng-click=\"selectPage(pageNumber)\">{{pageNumber}}</li>\n" +
	"    </ul>\n" +
	"\n" +
	"    <!-- Indicator of the existence of pages beyond the last page number shown -->\n" +
	"    <div class=\"more-pages\" ng-show=\"hasMorePagesAfter()\">...</div>\n" +
	"\n" +
	"    <!-- Next / Last -->\n" +
	"    <div class=\"next-page icon\" ng-class=\"{disabled: !canSelectPage(nextPage)}\" ng-click=\"selectPage(nextPage)\"/>\n" +
	"    <div class=\"last-page icon\" ng-class=\"{disabled: !canSelectPage(lastPage)}\" ng-click=\"selectPage(lastPage)\"/>\n" +
	"\n" +
	"</div>");
	$templateCache.put('app/login/templates/login.html',
	"<div class=\"login-ui\" ng-class=\"{error: loginError, continuation: isContinuation(), initial: !isContinuation()}\" >\n" +
	"    <!--\n" +
	"    Copyright 2014 Glyptodon LLC.\n" +
	"\n" +
	"    Permission is hereby granted, free of charge, to any person obtaining a copy\n" +
	"    of this software and associated documentation files (the \"Software\"), to deal\n" +
	"    in the Software without restriction, including without limitation the rights\n" +
	"    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n" +
	"    copies of the Software, and to permit persons to whom the Software is\n" +
	"    furnished to do so, subject to the following conditions:\n" +
	"\n" +
	"    The above copyright notice and this permission notice shall be included in\n" +
	"    all copies or substantial portions of the Software.\n" +
	"\n" +
	"    THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n" +
	"    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n" +
	"    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n" +
	"    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n" +
	"    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n" +
	"    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n" +
	"    THE SOFTWARE.\n" +
	"    -->\n" +
	"\n" +
	"    <!-- Login error message -->\n" +
	"    <p class=\"login-error\">{{loginError | translate}}</p>\n" +
	"\n" +
	"    <div class=\"login-dialog-middle\">\n" +
	"\n" +
	"        <div class=\"login-dialog\">\n" +
	"\n" +
	"            <form class=\"login-form\" ng-submit=\"login()\">\n" +
	"\n" +
	"                <!-- Guacamole version -->\n" +
	"                <div class=\"logo\"></div>\n" +
	"                <div class=\"version\">{{'APP.NAME' | translate}}</div>\n" +
	"\n" +
	"                <!-- Login message/instructions -->\n" +
	"                <p ng-show=\"helpText\">{{helpText | translate}}</p>\n" +
	"\n" +
	"                <!-- Login fields -->\n" +
	"                <div class=\"login-fields\">\n" +
	"                    <guac-form namespace=\"'LOGIN'\" content=\"remainingFields\" model=\"enteredValues\"></guac-form>\n" +
	"                </div>\n" +
	"\n" +
	"                <!-- Submit button -->\n" +
	"                <div class=\"buttons\">\n" +
	"                    <input type=\"submit\" name=\"login\" class=\"login\" value=\"{{'LOGIN.ACTION_LOGIN' | translate}}\"/>\n" +
	"                    <input type=\"submit\" name=\"login\" class=\"continue-login\" value=\"{{'LOGIN.ACTION_CONTINUE' | translate}}\"/>\n" +
	"                </div>\n" +
	"\n" +
	"            </form>\n" +
	"\n" +
	"        </div>\n" +
	"\n" +
	"    </div>\n" +
	"\n" +
	"</div>");
	$templateCache.put('app/manage/templates/connectionGroupPermission.html',
	"<div class=\"choice\">\n" +
	"    <!--\n" +
	"       Copyright (C) 2014 Glyptodon LLC\n" +
	"\n" +
	"       Permission is hereby granted, free of charge, to any person obtaining a copy\n" +
	"       of this software and associated documentation files (the \"Software\"), to deal\n" +
	"       in the Software without restriction, including without limitation the rights\n" +
	"       to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n" +
	"       copies of the Software, and to permit persons to whom the Software is\n" +
	"       furnished to do so, subject to the following conditions:\n" +
	"\n" +
	"       The above copyright notice and this permission notice shall be included in\n" +
	"       all copies or substantial portions of the Software.\n" +
	"\n" +
	"       THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n" +
	"       IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n" +
	"       FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n" +
	"       AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n" +
	"       LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n" +
	"       OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n" +
	"       THE SOFTWARE.\n" +
	"    -->\n" +
	"\n" +
	"    <input type=\"checkbox\" ng-model=\"context.getPermissionFlags().connectionGroupPermissions.READ[item.identifier]\"\n" +
	"                           ng-change=\"context.connectionGroupPermissionChanged(item.identifier)\"/>\n" +
	"\n" +
	"    <span class=\"name\">{{item.name}}</span>\n" +
	"</div>");
	$templateCache.put('app/manage/templates/connectionPermission.html',
	"<div class=\"choice\">\n" +
	"    <!--\n" +
	"       Copyright (C) 2014 Glyptodon LLC\n" +
	"\n" +
	"       Permission is hereby granted, free of charge, to any person obtaining a copy\n" +
	"       of this software and associated documentation files (the \"Software\"), to deal\n" +
	"       in the Software without restriction, including without limitation the rights\n" +
	"       to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n" +
	"       copies of the Software, and to permit persons to whom the Software is\n" +
	"       furnished to do so, subject to the following conditions:\n" +
	"\n" +
	"       The above copyright notice and this permission notice shall be included in\n" +
	"       all copies or substantial portions of the Software.\n" +
	"\n" +
	"       THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n" +
	"       IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n" +
	"       FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n" +
	"       AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n" +
	"       LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n" +
	"       OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n" +
	"       THE SOFTWARE.\n" +
	"    -->\n" +
	"\n" +
	"    <!-- Connection icon -->\n" +
	"    <div class=\"protocol\">\n" +
	"        <div class=\"icon type\" ng-class=\"item.protocol\"></div>\n" +
	"    </div>\n" +
	"\n" +
	"    <!-- Checkbox -->\n" +
	"    <input type=\"checkbox\" ng-model=\"context.getPermissionFlags().connectionPermissions.READ[item.identifier]\"\n" +
	"                           ng-change=\"context.connectionPermissionChanged(item.identifier)\"/>\n" +
	"\n" +
	"    <!-- Connection name -->\n" +
	"    <span class=\"name\">{{item.name}}</span>\n" +
	"\n" +
	"</div>");
	$templateCache.put('app/manage/templates/locationChooser.html',
	"<div class=\"location-chooser\">\n" +
	"    <!--\n" +
	"    Copyright 2014 Glyptodon LLC.\n" +
	"\n" +
	"    Permission is hereby granted, free of charge, to any person obtaining a copy\n" +
	"    of this software and associated documentation files (the \"Software\"), to deal\n" +
	"    in the Software without restriction, including without limitation the rights\n" +
	"    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n" +
	"    copies of the Software, and to permit persons to whom the Software is\n" +
	"    furnished to do so, subject to the following conditions:\n" +
	"\n" +
	"    The above copyright notice and this permission notice shall be included in\n" +
	"    all copies or substantial portions of the Software.\n" +
	"\n" +
	"    THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n" +
	"    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n" +
	"    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n" +
	"    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n" +
	"    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n" +
	"    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n" +
	"    THE SOFTWARE.\n" +
	"    -->\n" +
	"\n" +
	"    <!-- Chosen group name -->\n" +
	"    <div ng-click=\"toggleMenu()\" class=\"location\">{{chosenConnectionGroupName}}</div>\n" +
	"\n" +
	"    <!-- Dropdown hierarchical menu of groups -->\n" +
	"    <div ng-show=\"menuOpen\" class=\"dropdown\">\n" +
	"        <guac-group-list\n" +
	"            context=\"groupListContext\"\n" +
	"            show-root-group=\"true\"\n" +
	"            connection-groups=\"rootGroups\"\n" +
	"            connection-group-template=\"'app/manage/templates/locationChooserConnectionGroup.html'\"/>\n" +
	"    </div>\n" +
	"\n" +
	"</div>");
	$templateCache.put('app/manage/templates/locationChooserConnectionGroup.html',
	"<span class=\"name\" ng-click=\"context.chooseGroup(item.wrappedItem)\">\n" +
	"    <!--\n" +
	"       Copyright (C) 2014 Glyptodon LLC\n" +
	"\n" +
	"       Permission is hereby granted, free of charge, to any person obtaining a copy\n" +
	"       of this software and associated documentation files (the \"Software\"), to deal\n" +
	"       in the Software without restriction, including without limitation the rights\n" +
	"       to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n" +
	"       copies of the Software, and to permit persons to whom the Software is\n" +
	"       furnished to do so, subject to the following conditions:\n" +
	"\n" +
	"       The above copyright notice and this permission notice shall be included in\n" +
	"       all copies or substantial portions of the Software.\n" +
	"\n" +
	"       THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n" +
	"       IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n" +
	"       FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n" +
	"       AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n" +
	"       LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n" +
	"       OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n" +
	"       THE SOFTWARE.\n" +
	"    -->\n" +
	"\n" +
	"    {{item.name}}\n" +
	"</span>");
	$templateCache.put('app/manage/templates/manageConnection.html',
	"<!--\n" +
	"Copyright 2014 Glyptodon LLC.\n" +
	"\n" +
	"Permission is hereby granted, free of charge, to any person obtaining a copy\n" +
	"of this software and associated documentation files (the \"Software\"), to deal\n" +
	"in the Software without restriction, including without limitation the rights\n" +
	"to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n" +
	"copies of the Software, and to permit persons to whom the Software is\n" +
	"furnished to do so, subject to the following conditions:\n" +
	"\n" +
	"The above copyright notice and this permission notice shall be included in\n" +
	"all copies or substantial portions of the Software.\n" +
	"\n" +
	"THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n" +
	"IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n" +
	"FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n" +
	"AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n" +
	"LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n" +
	"OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n" +
	"THE SOFTWARE.\n" +
	"-->\n" +
	"\n" +
	"<div class=\"view\" ng-class=\"{loading: !isLoaded()}\">\n" +
	"\n" +
	"    <!-- Main property editor -->\n" +
	"    <div class=\"header\">\n" +
	"        <h2>{{'MANAGE_CONNECTION.SECTION_HEADER_EDIT_CONNECTION' | translate}}</h2>\n" +
	"        <guac-user-menu></guac-user-menu>\n" +
	"    </div>\n" +
	"    <div class=\"section\">\n" +
	"        <table class=\"properties\">\n" +
	"            \n" +
	"            <!-- Edit connection name -->\n" +
	"            <tr>\n" +
	"                <th>{{'MANAGE_CONNECTION.FIELD_HEADER_NAME' | translate}}</th>\n" +
	"              \n" +
	"                <td><input type=\"text\" ng-model=\"connection.name\" autocorrect=\"off\" autocapitalize=\"off\"/></td>\n" +
	"            </tr>\n" +
	"            \n" +
	"            <!-- Edit connection location -->\n" +
	"            <tr>\n" +
	"                <th>{{'MANAGE_CONNECTION.FIELD_HEADER_LOCATION' | translate}}</th>\n" +
	"              \n" +
	"                <td>\n" +
	"                    <location-chooser\n" +
	"                        data-data-source=\"selectedDataSource\" root-group=\"rootGroup\"\n" +
	"                        value=\"connection.parentIdentifier\"></location-chooser>\n" +
	"                </td>\n" +
	"            </tr>\n" +
	"            \n" +
	"            \n" +
	"            <!-- Edit connection protocol -->\n" +
	"            <tr>\n" +
	"                <th>{{'MANAGE_CONNECTION.FIELD_HEADER_PROTOCOL' | translate}}</th>\n" +
	"                <td>\n" +
	"                    <select ng-model=\"connection.protocol\" ng-options=\"name as getProtocolName(protocol.name) | translate for (name, protocol) in protocols | orderBy: name\"></select>\n" +
	"                </td>\n" +
	"            </tr>\n" +
	"        </table>\n" +
	"    </div>\n" +
	"\n" +
	"    <!-- Connection attributes section -->\n" +
	"    <div class=\"attributes\">\n" +
	"        <guac-form namespace=\"'CONNECTION_ATTRIBUTES'\" content=\"attributes\" model=\"connection.attributes\"></guac-form>\n" +
	"    </div>\n" +
	"\n" +
	"    <!-- Connection parameters -->\n" +
	"    <h2 class=\"header\">{{'MANAGE_CONNECTION.SECTION_HEADER_PARAMETERS' | translate}}</h2>\n" +
	"    <div class=\"section connection-parameters\" ng-class=\"{loading: !parameters}\">\n" +
	"        <guac-form namespace=\"getNamespace(connection.protocol)\"\n" +
	"                   content=\"protocols[connection.protocol].forms\"\n" +
	"                   model=\"parameters\"></guac-form>\n" +
	"    </div>\n" +
	"\n" +
	"    <!-- Form action buttons -->\n" +
	"    <div class=\"action-buttons\">\n" +
	"        <button ng-show=\"canSaveConnection\" ng-click=\"saveConnection()\">{{'MANAGE_CONNECTION.ACTION_SAVE' | translate}}</button>\n" +
	"        <button ng-show=\"canCloneConnection\" ng-click=\"cloneConnection()\">{{'MANAGE_CONNECTION.ACTION_CLONE' | translate}}</button>\n" +
	"        <button ng-click=\"cancel()\">{{'MANAGE_CONNECTION.ACTION_CANCEL' | translate}}</button>\n" +
	"        <button ng-show=\"canDeleteConnection\" ng-click=\"deleteConnection()\" class=\"danger\">{{'MANAGE_CONNECTION.ACTION_DELETE' | translate}}</button>\n" +
	"    </div>\n" +
	"\n" +
	"    <!-- Connection history -->\n" +
	"    <h2 class=\"header\">{{'MANAGE_CONNECTION.SECTION_HEADER_HISTORY' | translate}}</h2>\n" +
	"    <div class=\"history section\" ng-class=\"{loading: !historyEntryWrappers}\">\n" +
	"        <p ng-hide=\"historyEntryWrappers.length\">{{'MANAGE_CONNECTION.INFO_CONNECTION_NOT_USED' | translate}}</p>\n" +
	"\n" +
	"        <!-- History list -->\n" +
	"        <table ng-show=\"historyEntryWrappers.length\">\n" +
	"            <thead>\n" +
	"                <tr>\n" +
	"                    <th>{{'MANAGE_CONNECTION.TABLE_HEADER_HISTORY_USERNAME' | translate}}</th>\n" +
	"                    <th>{{'MANAGE_CONNECTION.TABLE_HEADER_HISTORY_START' | translate}}</th>\n" +
	"                    <th>{{'MANAGE_CONNECTION.TABLE_HEADER_HISTORY_DURATION' | translate}}</th>\n" +
	"                </tr>\n" +
	"            </thead>\n" +
	"            <tbody>\n" +
	"                <tr ng-repeat=\"wrapper in wrapperPage\">\n" +
	"                    <td class=\"username\">{{wrapper.entry.username}}</td>\n" +
	"                    <td class=\"start\">{{wrapper.entry.startDate | date:historyDateFormat}}</td>\n" +
	"                    <td class=\"duration\"\n" +
	"                        translate=\"{{wrapper.durationText}}\"\n" +
	"                        translate-values=\"{VALUE: wrapper.duration.value, UNIT: wrapper.duration.unit}\"></td>\n" +
	"                </tr>\n" +
	"            </tbody>\n" +
	"        </table>\n" +
	"\n" +
	"        <!-- Pager controls for history list -->\n" +
	"        <guac-pager page=\"wrapperPage\" items=\"historyEntryWrappers\"></guac-pager>\n" +
	"\n" +
	"    </div>\n" +
	"\n" +
	"</div>");
	$templateCache.put('app/manage/templates/manageConnectionGroup.html',
	"<!--\n" +
	"Copyright 2014 Glyptodon LLC.\n" +
	"\n" +
	"Permission is hereby granted, free of charge, to any person obtaining a copy\n" +
	"of this software and associated documentation files (the \"Software\"), to deal\n" +
	"in the Software without restriction, including without limitation the rights\n" +
	"to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n" +
	"copies of the Software, and to permit persons to whom the Software is\n" +
	"furnished to do so, subject to the following conditions:\n" +
	"\n" +
	"The above copyright notice and this permission notice shall be included in\n" +
	"all copies or substantial portions of the Software.\n" +
	"\n" +
	"THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n" +
	"IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n" +
	"FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n" +
	"AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n" +
	"LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n" +
	"OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n" +
	"THE SOFTWARE.\n" +
	"-->\n" +
	"\n" +
	"<div class=\"view\" ng-class=\"{loading: !isLoaded()}\">\n" +
	"\n" +
	"    <!-- Main property editor -->\n" +
	"    <div class=\"header\">\n" +
	"        <h2>{{'MANAGE_CONNECTION_GROUP.SECTION_HEADER_EDIT_CONNECTION_GROUP' | translate}}</h2>\n" +
	"        <guac-user-menu></guac-user-menu>\n" +
	"    </div>\n" +
	"    <div class=\"section\">\n" +
	"        <table class=\"properties\">\n" +
	"                        \n" +
	"            <!-- Edit connection group name -->\n" +
	"            <tr>\n" +
	"                <th>{{'MANAGE_CONNECTION_GROUP.FIELD_HEADER_NAME' | translate}}</th>\n" +
	"                          \n" +
	"                <td><input type=\"text\" ng-model=\"connectionGroup.name\" autocorrect=\"off\" autocapitalize=\"off\"/></td>\n" +
	"            </tr>\n" +
	"                        \n" +
	"            <!-- Edit connection group location -->\n" +
	"            <tr>\n" +
	"                <th>{{'MANAGE_CONNECTION_GROUP.FIELD_HEADER_LOCATION' | translate}}</th>\n" +
	"                          \n" +
	"                <td>\n" +
	"                    <location-chooser\n" +
	"                        data-data-source=\"selectedDataSource\" root-group=\"rootGroup\"\n" +
	"                        value=\"connectionGroup.parentIdentifier\"></location-chooser>\n" +
	"                </td>\n" +
	"            </tr>\n" +
	"                        \n" +
	"                        \n" +
	"            <!-- Edit connection group type -->\n" +
	"            <tr>\n" +
	"                <th>{{'MANAGE_CONNECTION_GROUP.FIELD_HEADER_TYPE' | translate}}</th>\n" +
	"                <td>\n" +
	"                    <select ng-model=\"connectionGroup.type\" ng-options=\"type.value as type.label | translate for type in types | orderBy: name\"></select>\n" +
	"                </td>\n" +
	"            </tr>\n" +
	"        </table>\n" +
	"    </div>\n" +
	"\n" +
	"    <!-- Connection group attributes section -->\n" +
	"    <div class=\"attributes\">\n" +
	"        <guac-form namespace=\"'CONNECTION_GROUP_ATTRIBUTES'\" content=\"attributes\" model=\"connectionGroup.attributes\"></guac-form>\n" +
	"    </div>\n" +
	"\n" +
	"    <!-- Form action buttons -->\n" +
	"    <div class=\"action-buttons\">\n" +
	"        <button ng-show=\"canSaveConnectionGroup\" ng-click=\"saveConnectionGroup()\">{{'MANAGE_CONNECTION_GROUP.ACTION_SAVE' | translate}}</button>\n" +
	"        <button ng-click=\"cancel()\">{{'MANAGE_CONNECTION_GROUP.ACTION_CANCEL' | translate}}</button>\n" +
	"        <button ng-show=\"canDeleteConnectionGroup\" ng-click=\"deleteConnectionGroup()\" class=\"danger\">{{'MANAGE_CONNECTION_GROUP.ACTION_DELETE' | translate}}</button>\n" +
	"    </div>\n" +
	"\n" +
	"</div>");
	$templateCache.put('app/manage/templates/manageUser.html',
	"<!--\n" +
	"Copyright 2015 Glyptodon LLC.\n" +
	"\n" +
	"Permission is hereby granted, free of charge, to any person obtaining a copy\n" +
	"of this software and associated documentation files (the \"Software\"), to deal\n" +
	"in the Software without restriction, including without limitation the rights\n" +
	"to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n" +
	"copies of the Software, and to permit persons to whom the Software is\n" +
	"furnished to do so, subject to the following conditions:\n" +
	"\n" +
	"The above copyright notice and this permission notice shall be included in\n" +
	"all copies or substantial portions of the Software.\n" +
	"\n" +
	"THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n" +
	"IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n" +
	"FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n" +
	"AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n" +
	"LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n" +
	"OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n" +
	"THE SOFTWARE.\n" +
	"-->\n" +
	"\n" +
	"<div class=\"manage-user view\" ng-class=\"{loading: !isLoaded()}\">\n" +
	"\n" +
	"    <!-- User header and data source tabs -->\n" +
	"    <div class=\"username header\">\n" +
	"        <h2>{{'MANAGE_USER.SECTION_HEADER_EDIT_USER' | translate}}</h2>\n" +
	"        <guac-user-menu></guac-user-menu>\n" +
	"    </div>\n" +
	"    <div class=\"page-tabs\">\n" +
	"        <guac-page-list pages=\"accountPages\"></guac-page-list>\n" +
	"    </div>\n" +
	"\n" +
	"    <!-- Warn if user is read-only -->\n" +
	"    <div class=\"section\" ng-show=\"isReadOnly()\">\n" +
	"        <p class=\"notice read-only\">{{'MANAGE_USER.INFO_READ_ONLY' | translate}}</p>\n" +
	"    </div>\n" +
	"\n" +
	"    <!-- Sections applicable to non-read-only users -->\n" +
	"    <div ng-show=\"!isReadOnly()\">\n" +
	"\n" +
	"        <!-- User password section -->\n" +
	"        <div class=\"section\">\n" +
	"            <table class=\"properties\">\n" +
	"                <tr>\n" +
	"                    <th>{{'MANAGE_USER.FIELD_HEADER_USERNAME' | translate}}</th>\n" +
	"                    <td>\n" +
	"                        <input ng-show=\"canEditUsername()\" ng-model=\"user.username\" type=\"text\"/>\n" +
	"                        <span  ng-hide=\"canEditUsername()\">{{user.username}}</span>\n" +
	"                    </td>\n" +
	"                </tr>\n" +
	"                <tr>\n" +
	"                    <th>{{'MANAGE_USER.FIELD_HEADER_PASSWORD' | translate}}</th>\n" +
	"                    <td><input ng-model=\"user.password\" type=\"password\" /></td>\n" +
	"                </tr>\n" +
	"                <tr>\n" +
	"                    <th>{{'MANAGE_USER.FIELD_HEADER_PASSWORD_AGAIN' | translate}}</th>\n" +
	"                    <td><input ng-model=\"passwordMatch\" type=\"password\" /></td>\n" +
	"                </tr>\n" +
	"            </table>\n" +
	"        </div>\n" +
	"\n" +
	"        <!-- User attributes section -->\n" +
	"        <div class=\"attributes\" ng-show=\"canChangeAttributes()\">\n" +
	"            <guac-form namespace=\"'USER_ATTRIBUTES'\" content=\"attributes\" model=\"user.attributes\"></guac-form>\n" +
	"        </div>\n" +
	"\n" +
	"        <!-- System permissions section -->\n" +
	"        <div class=\"system-permissions\" ng-show=\"canChangePermissions()\">\n" +
	"            <h2 class=\"header\">{{'MANAGE_USER.SECTION_HEADER_PERMISSIONS' | translate}}</h2>\n" +
	"            <div class=\"section\">\n" +
	"                <table class=\"properties\">\n" +
	"                    <tr ng-repeat=\"systemPermissionType in systemPermissionTypes\"\n" +
	"                        ng-show=\"canChangeSystemPermissions()\">\n" +
	"                        <th>{{systemPermissionType.label | translate}}</th>\n" +
	"                        <td><input type=\"checkbox\" ng-model=\"permissionFlags.systemPermissions[systemPermissionType.value]\"\n" +
	"                                                   ng-change=\"systemPermissionChanged(systemPermissionType.value)\"/></td>\n" +
	"                    </tr>\n" +
	"                    <tr>\n" +
	"                        <th>{{'MANAGE_USER.FIELD_HEADER_CHANGE_OWN_PASSWORD' | translate}}</th>\n" +
	"                        <td><input type=\"checkbox\" ng-model=\"permissionFlags.userPermissions.UPDATE[user.username]\"\n" +
	"                                                   ng-change=\"userPermissionChanged('UPDATE', user.username)\"/></td>\n" +
	"                    </tr>\n" +
	"                </table>\n" +
	"            </div>\n" +
	"        </div>\n" +
	"\n" +
	"        <!-- Connection permissions section -->\n" +
	"        <div class=\"connection-permissions\" ng-show=\"canChangePermissions()\">\n" +
	"            <div class=\"header\">\n" +
	"                <h2>{{'MANAGE_USER.SECTION_HEADER_CONNECTIONS' | translate}}</h2>\n" +
	"                <guac-group-list-filter connection-groups=\"rootGroups\"\n" +
	"                    filtered-connection-groups=\"filteredRootGroups\"\n" +
	"                    placeholder=\"'MANAGE_USER.FIELD_PLACEHOLDER_FILTER' | translate\"\n" +
	"                    connection-properties=\"filteredConnectionProperties\"\n" +
	"                    connection-group-properties=\"filteredConnectionGroupProperties\"></guac-group-list-filter>\n" +
	"            </div>\n" +
	"            <div class=\"section\">\n" +
	"                <guac-group-list\n" +
	"                    context=\"groupListContext\"\n" +
	"                    connection-groups=\"filteredRootGroups\"\n" +
	"                    connection-template=\"'app/manage/templates/connectionPermission.html'\"\n" +
	"                    connection-group-template=\"'app/manage/templates/connectionGroupPermission.html'\"\n" +
	"                    page-size=\"20\"/>\n" +
	"            </div>\n" +
	"        </div>\n" +
	"\n" +
	"        <!-- Form action buttons -->\n" +
	"        <div class=\"action-buttons\">\n" +
	"            <button ng-show=\"canSaveUser()\" ng-click=\"saveUser()\">{{'MANAGE_USER.ACTION_SAVE' | translate}}</button>\n" +
	"            <button ng-click=\"cancel()\">{{'MANAGE_USER.ACTION_CANCEL' | translate}}</button>\n" +
	"            <button ng-show=\"canDeleteUser()\" ng-click=\"deleteUser()\" class=\"danger\">{{'MANAGE_USER.ACTION_DELETE' | translate}}</button>\n" +
	"        </div>\n" +
	"\n" +
	"    </div>\n" +
	"\n" +
	"</div>");
	$templateCache.put('app/navigation/templates/guacPageList.html',
	"<div class=\"page-list\" ng-show=\"levels.length\">\n" +
	"    <!--\n" +
	"       Copyright (C) 2015 Glyptodon LLC\n" +
	"\n" +
	"       Permission is hereby granted, free of charge, to any person obtaining a copy\n" +
	"       of this software and associated documentation files (the \"Software\"), to deal\n" +
	"       in the Software without restriction, including without limitation the rights\n" +
	"       to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n" +
	"       copies of the Software, and to permit persons to whom the Software is\n" +
	"       furnished to do so, subject to the following conditions:\n" +
	"\n" +
	"       The above copyright notice and this permission notice shall be included in\n" +
	"       all copies or substantial portions of the Software.\n" +
	"\n" +
	"       THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n" +
	"       IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n" +
	"       FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n" +
	"       AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n" +
	"       LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n" +
	"       OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n" +
	"       THE SOFTWARE.\n" +
	"    -->\n" +
	"\n" +
	"    <!-- Navigation links -->\n" +
	"    <ul class=\"page-list-level\" ng-repeat=\"level in levels track by $index\">\n" +
	"        <li ng-repeat=\"page in getPages(level)\" class=\"{{page.className}}\">\n" +
	"            <a class=\"home\" ng-click=\"navigateToPage(page)\"\n" +
	"               ng-class=\"{current: isCurrentPage(page)}\" href=\"#{{page.url}}\">\n" +
	"                {{page.name | translate}}\n" +
	"            </a>\n" +
	"        </li>\n" +
	"    </ul>\n" +
	"\n" +
	"</div>");
	$templateCache.put('app/navigation/templates/guacUserMenu.html',
	"<div class=\"user-menu\">\n" +
	"    <!--\n" +
	"       Copyright (C) 2015 Glyptodon LLC\n" +
	"\n" +
	"       Permission is hereby granted, free of charge, to any person obtaining a copy\n" +
	"       of this software and associated documentation files (the \"Software\"), to deal\n" +
	"       in the Software without restriction, including without limitation the rights\n" +
	"       to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n" +
	"       copies of the Software, and to permit persons to whom the Software is\n" +
	"       furnished to do so, subject to the following conditions:\n" +
	"\n" +
	"       The above copyright notice and this permission notice shall be included in\n" +
	"       all copies or substantial portions of the Software.\n" +
	"\n" +
	"       THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n" +
	"       IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n" +
	"       FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n" +
	"       AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n" +
	"       LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n" +
	"       OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n" +
	"       THE SOFTWARE.\n" +
	"    -->\n" +
	"\n" +
	"    <div class=\"user-menu-dropdown\" ng-class=\"{open: menuShown}\" ng-click=\"toggleMenu()\">\n" +
	"        <div class=\"username\">{{username}}</div>\n" +
	"        <div class=\"menu-indicator\"></div>\n" +
	"        \n" +
	"        <!-- Menu options -->\n" +
	"        <div class=\"options\">\n" +
	"            \n" +
	"            <!-- Local actions -->\n" +
	"            <ul class=\"action-list\">\n" +
	"                <li ng-repeat=\"action in localActions\">\n" +
	"                    <a ng-class=\"action.className\" ng-click=\"action.callback()\">\n" +
	"                        {{action.name | translate}}\n" +
	"                    </a>\n" +
	"                </li>\n" +
	"            </ul>\n" +
	"\n" +
	"            <!-- Navigation links -->\n" +
	"            <guac-page-list pages=\"pages\"></guac-page-list>\n" +
	"\n" +
	"            <!-- Actions -->\n" +
	"            <ul class=\"action-list\">\n" +
	"                <li ng-repeat=\"action in actions\">\n" +
	"                    <a ng-class=\"action.className\" ng-click=\"action.callback()\">\n" +
	"                        {{action.name | translate}}\n" +
	"                    </a>\n" +
	"                </li>\n" +
	"            </ul>\n" +
	"\n" +
	"        </div>\n" +
	"    </div>\n" +
	"\n" +
	"</div>");
	$templateCache.put('app/notification/templates/guacNotification.html',
	"<div class=\"notification\" ng-class=\"notification.className\">\n" +
	"    <!--\n" +
	"       Copyright (C) 2014 Glyptodon LLC\n" +
	"\n" +
	"       Permission is hereby granted, free of charge, to any person obtaining a copy\n" +
	"       of this software and associated documentation files (the \"Software\"), to deal\n" +
	"       in the Software without restriction, including without limitation the rights\n" +
	"       to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n" +
	"       copies of the Software, and to permit persons to whom the Software is\n" +
	"       furnished to do so, subject to the following conditions:\n" +
	"\n" +
	"       The above copyright notice and this permission notice shall be included in\n" +
	"       all copies or substantial portions of the Software.\n" +
	"\n" +
	"       THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n" +
	"       IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n" +
	"       FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n" +
	"       AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n" +
	"       LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n" +
	"       OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n" +
	"       THE SOFTWARE.\n" +
	"    -->\n" +
	"\n" +
	"    <!-- Notification title -->\n" +
	"    <div ng-show=\"notification.title\" class=\"title-bar\">\n" +
	"        <div class=\"title\">{{notification.title | translate}}</div>\n" +
	"    </div>\n" +
	"\n" +
	"    <div class=\"body\">\n" +
	"\n" +
	"        <!-- Notification text -->\n" +
	"        <p ng-show=\"notification.text\" class=\"text\">{{notification.text | translate}}</p>\n" +
	"\n" +
	"        <!-- Current progress -->\n" +
	"        <div class=\"progress\" ng-show=\"notification.progress\"><div class=\"bar\" ng-show=\"progressPercent\" ng-style=\"{'width': progressPercent + '%'}\"></div><div\n" +
	"                ng-show=\"notification.progress.text\"\n" +
	"                translate=\"{{notification.progress.text}}\"\n" +
	"                translate-values=\"{PROGRESS: notification.progress.value, UNIT: notification.progress.unit}\"></div></div>\n" +
	"\n" +
	"        <!-- Default action countdown text -->\n" +
	"        <p class=\"countdown-text\"\n" +
	"           ng-show=\"notification.countdown.text\"\n" +
	"           translate=\"{{notification.countdown.text}}\"\n" +
	"           translate-values=\"{REMAINING: timeRemaining}\"></p>\n" +
	"\n" +
	"    </div>\n" +
	"\n" +
	"    <!-- Buttons -->\n" +
	"    <div ng-show=\"notification.actions.length\" class=\"buttons\">\n" +
	"        <button ng-repeat=\"action in notification.actions\" ng-click=\"action.callback()\" ng-class=\"action.className\">{{action.name | translate}}</button>\n" +
	"    </div>\n" +
	"\n" +
	"</div>");
	$templateCache.put('app/osk/templates/guacOsk.html',
	"<div class=\"osk\" guac-resize=\"keyboardResized\">\n" +
	"    <!--\n" +
	"       Copyright (C) 2014 Glyptodon LLC\n" +
	"\n" +
	"       Permission is hereby granted, free of charge, to any person obtaining a copy\n" +
	"       of this software and associated documentation files (the \"Software\"), to deal\n" +
	"       in the Software without restriction, including without limitation the rights\n" +
	"       to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n" +
	"       copies of the Software, and to permit persons to whom the Software is\n" +
	"       furnished to do so, subject to the following conditions:\n" +
	"\n" +
	"       The above copyright notice and this permission notice shall be included in\n" +
	"       all copies or substantial portions of the Software.\n" +
	"\n" +
	"       THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n" +
	"       IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n" +
	"       FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n" +
	"       AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n" +
	"       LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n" +
	"       OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n" +
	"       THE SOFTWARE.\n" +
	"    -->\n" +
	"</div>");
	$templateCache.put('app/settings/templates/connection.html',
	"<a ng-href=\"#/manage/{{item.dataSource}}/connections/{{item.identifier}}\">\n" +
	"    <!--\n" +
	"       Copyright (C) 2014 Glyptodon LLC\n" +
	"\n" +
	"       Permission is hereby granted, free of charge, to any person obtaining a copy\n" +
	"       of this software and associated documentation files (the \"Software\"), to deal\n" +
	"       in the Software without restriction, including without limitation the rights\n" +
	"       to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n" +
	"       copies of the Software, and to permit persons to whom the Software is\n" +
	"       furnished to do so, subject to the following conditions:\n" +
	"\n" +
	"       The above copyright notice and this permission notice shall be included in\n" +
	"       all copies or substantial portions of the Software.\n" +
	"\n" +
	"       THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n" +
	"       IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n" +
	"       FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n" +
	"       AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n" +
	"       LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n" +
	"       OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n" +
	"       THE SOFTWARE.\n" +
	"    -->\n" +
	"\n" +
	"    <div class=\"caption\" ng-class=\"{active: item.getActiveConnections()}\">\n" +
	"\n" +
	"        <!-- Connection icon -->\n" +
	"        <div class=\"protocol\">\n" +
	"            <div class=\"icon type\" ng-class=\"item.protocol\"></div>\n" +
	"        </div>\n" +
	"\n" +
	"        <!-- Connection name -->\n" +
	"        <span class=\"name\">{{item.name}}</span>\n" +
	"\n" +
	"        <!-- Active user count -->\n" +
	"        <span class=\"activeUserCount\" ng-show=\"item.getActiveConnections()\"\n" +
	"            translate=\"SETTINGS_CONNECTIONS.INFO_ACTIVE_USER_COUNT\"\n" +
	"            translate-values=\"{USERS: item.getActiveConnections()}\"></span>\n" +
	"        \n" +
	"    </div>\n" +
	"</a>");
	$templateCache.put('app/settings/templates/connectionGroup.html',
	"<a ng-href=\"#/manage/{{item.dataSource}}/connectionGroups/{{item.identifier}}\">\n" +
	"    <!--\n" +
	"       Copyright (C) 2014 Glyptodon LLC\n" +
	"\n" +
	"       Permission is hereby granted, free of charge, to any person obtaining a copy\n" +
	"       of this software and associated documentation files (the \"Software\"), to deal\n" +
	"       in the Software without restriction, including without limitation the rights\n" +
	"       to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n" +
	"       copies of the Software, and to permit persons to whom the Software is\n" +
	"       furnished to do so, subject to the following conditions:\n" +
	"\n" +
	"       The above copyright notice and this permission notice shall be included in\n" +
	"       all copies or substantial portions of the Software.\n" +
	"\n" +
	"       THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n" +
	"       IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n" +
	"       FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n" +
	"       AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n" +
	"       LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n" +
	"       OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n" +
	"       THE SOFTWARE.\n" +
	"    -->\n" +
	"\n" +
	"    <span class=\"name\">{{item.name}}</span>\n" +
	"</a>");
	$templateCache.put('app/settings/templates/settings.html',
	"<!--\n" +
	"Copyright 2015 Glyptodon LLC.\n" +
	"\n" +
	"Permission is hereby granted, free of charge, to any person obtaining a copy\n" +
	"of this software and associated documentation files (the \"Software\"), to deal\n" +
	"in the Software without restriction, including without limitation the rights\n" +
	"to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n" +
	"copies of the Software, and to permit persons to whom the Software is\n" +
	"furnished to do so, subject to the following conditions:\n" +
	"\n" +
	"The above copyright notice and this permission notice shall be included in\n" +
	"all copies or substantial portions of the Software.\n" +
	"\n" +
	"THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n" +
	"IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n" +
	"FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n" +
	"AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n" +
	"LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n" +
	"OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n" +
	"THE SOFTWARE.\n" +
	"-->\n" +
	"\n" +
	"<div class=\"view\">\n" +
	"\n" +
	"    <div class=\"header\">\n" +
	"        <h2>{{'SETTINGS.SECTION_HEADER_SETTINGS' | translate}}</h2>\n" +
	"        <guac-user-menu></guac-user-menu>\n" +
	"    </div>\n" +
	"\n" +
	"    <!-- Available tabs -->\n" +
	"    <div class=\"page-tabs\">\n" +
	"        <guac-page-list pages=\"settingsPages\"></guac-page-list>\n" +
	"    </div>\n" +
	"\n" +
	"    <!-- Selected tab -->\n" +
	"    <guac-settings-users                ng-if=\"activeTab === 'users'\"></guac-settings-users>\n" +
	"    <guac-settings-connections          ng-if=\"activeTab === 'connections'\"></guac-settings-connections>\n" +
	"    <guac-settings-connection-history   ng-if=\"activeTab === 'history'\"></guac-settings-connection-history>\n" +
	"    <guac-settings-sessions             ng-if=\"activeTab === 'sessions'\"></guac-settings-sessions>\n" +
	"    <guac-settings-preferences          ng-if=\"activeTab === 'preferences'\"></guac-settings-preferences>\n" +
	"\n" +
	"</div>");
	$templateCache.put('app/settings/templates/settingsConnectionHistory.html',
	"<div class=\"settings section connectionHistory\">\n" +
	"    <!--\n" +
	"    Copyright 2015 Glyptodon LLC.\n" +
	"\n" +
	"    Permission is hereby granted, free of charge, to any person obtaining a copy\n" +
	"    of this software and associated documentation files (the \"Software\"), to deal\n" +
	"    in the Software without restriction, including without limitation the rights\n" +
	"    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n" +
	"    copies of the Software, and to permit persons to whom the Software is\n" +
	"    furnished to do so, subject to the following conditions:\n" +
	"\n" +
	"    The above copyright notice and this permission notice shall be included in\n" +
	"    all copies or substantial portions of the Software.\n" +
	"\n" +
	"    THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n" +
	"    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n" +
	"    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n" +
	"    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n" +
	"    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n" +
	"    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n" +
	"    THE SOFTWARE.\n" +
	"    -->\n" +
	"\n" +
	"    <!-- Connection history -->\n" +
	"    <p>{{'SETTINGS_CONNECTION_HISTORY.HELP_CONNECTION_HISTORY' | translate}}</p>\n" +
	"\n" +
	"    <!-- Search controls -->\n" +
	"    <form class=\"filter\" ng-submit=\"search()\">\n" +
	"        <input class=\"search-string\" type=\"text\" placeholder=\"{{'SETTINGS_CONNECTION_HISTORY.FIELD_PLACEHOLDER_FILTER' | translate}}\" ng-model=\"searchString\" />\n" +
	"        <input class=\"search-button\" type=\"submit\" value=\"{{'SETTINGS_CONNECTION_HISTORY.ACTION_SEARCH' | translate}}\" />\n" +
	"    </form>\n" +
	"\n" +
	"    <!-- Search results -->\n" +
	"    <div class=\"results\">\n" +
	"\n" +
	"        <!-- List of matching history records -->\n" +
	"        <table class=\"sorted history-list\">\n" +
	"            <thead>\n" +
	"                <tr>\n" +
	"                    <th guac-sort-order=\"order\" guac-sort-property=\"'username'\">\n" +
	"                        {{'SETTINGS_CONNECTION_HISTORY.TABLE_HEADER_SESSION_USERNAME' | translate}}\n" +
	"                    </th>\n" +
	"                    <th guac-sort-order=\"order\" guac-sort-property=\"'startDate'\">\n" +
	"                        {{'SETTINGS_CONNECTION_HISTORY.TABLE_HEADER_SESSION_STARTDATE' | translate}}\n" +
	"                    </th>\n" +
	"                    <th guac-sort-order=\"order\" guac-sort-property=\"'duration'\">\n" +
	"                        {{'SETTINGS_CONNECTION_HISTORY.TABLE_HEADER_SESSION_DURATION' | translate}}\n" +
	"                    </th>\n" +
	"                    <th guac-sort-order=\"order\" guac-sort-property=\"'connectionName'\">\n" +
	"                        {{'SETTINGS_CONNECTION_HISTORY.TABLE_HEADER_SESSION_CONNECTION_NAME' | translate}}\n" +
	"                    </th>\n" +
	"                </tr>\n" +
	"            </thead>\n" +
	"            <tbody ng-class=\"{loading: !isLoaded()}\">\n" +
	"                <tr ng-repeat=\"historyEntryWrapper in historyEntryWrapperPage\" class=\"history\">\n" +
	"                    <td>{{historyEntryWrapper.username}}</td>\n" +
	"                    <td>{{historyEntryWrapper.startDate | date : dateFormat}}</td>\n" +
	"                    <td translate=\"{{historyEntryWrapper.readableDurationText}}\"\n" +
	"                        translate-values=\"{VALUE: historyEntryWrapper.readableDuration.value, UNIT: historyEntryWrapper.readableDuration.unit}\"></td>\n" +
	"                    <td>{{historyEntryWrapper.connectionName}}</td>\n" +
	"                </tr>\n" +
	"            </tbody>\n" +
	"        </table>\n" +
	"\n" +
	"        <!-- Text displayed if no history exists -->\n" +
	"        <p class=\"placeholder\" ng-show=\"isHistoryEmpty()\">\n" +
	"            {{'SETTINGS_CONNECTION_HISTORY.INFO_NO_HISTORY' | translate}}\n" +
	"        </p>\n" +
	"\n" +
	"        <!-- Pager for history list -->\n" +
	"        <guac-pager page=\"historyEntryWrapperPage\" page-size=\"25\"\n" +
	"                    items=\"historyEntryWrappers | orderBy : order.predicate\"></guac-pager>\n" +
	"    </div>\n" +
	"\n" +
	"</div>");
	$templateCache.put('app/settings/templates/settingsConnections.html',
	"<div class=\"settings section connections\" ng-class=\"{loading: !isLoaded()}\">\n" +
	"    <!--\n" +
	"    Copyright 2015 Glyptodon LLC.\n" +
	"\n" +
	"    Permission is hereby granted, free of charge, to any person obtaining a copy\n" +
	"    of this software and associated documentation files (the \"Software\"), to deal\n" +
	"    in the Software without restriction, including without limitation the rights\n" +
	"    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n" +
	"    copies of the Software, and to permit persons to whom the Software is\n" +
	"    furnished to do so, subject to the following conditions:\n" +
	"\n" +
	"    The above copyright notice and this permission notice shall be included in\n" +
	"    all copies or substantial portions of the Software.\n" +
	"\n" +
	"    THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n" +
	"    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n" +
	"    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n" +
	"    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n" +
	"    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n" +
	"    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n" +
	"    THE SOFTWARE.\n" +
	"    -->\n" +
	"\n" +
	"    <!-- Connection management -->\n" +
	"    <p>{{'SETTINGS_CONNECTIONS.HELP_CONNECTIONS' | translate}}</p>\n" +
	"\n" +
	"    <!-- Connection management toolbar -->\n" +
	"    <div class=\"toolbar\">\n" +
	"\n" +
	"        <!-- Form action buttons -->\n" +
	"        <div class=\"action-buttons\">\n" +
	"\n" +
	"            <a class=\"add-connection button\"\n" +
	"               ng-show=\"canCreateConnections()\"\n" +
	"               href=\"#/manage/{{dataSource}}/connections/\">{{'SETTINGS_CONNECTIONS.ACTION_NEW_CONNECTION' | translate}}</a>\n" +
	"\n" +
	"            <a class=\"add-connection-group button\"\n" +
	"               ng-show=\"canCreateConnectionGroups()\"\n" +
	"               href=\"#/manage/{{dataSource}}/connectionGroups/\">{{'SETTINGS_CONNECTIONS.ACTION_NEW_CONNECTION_GROUP' | translate}}</a>\n" +
	"\n" +
	"        </div>\n" +
	"\n" +
	"        <!-- Connection filter -->\n" +
	"        <guac-group-list-filter connection-groups=\"rootGroups\"\n" +
	"            filtered-connection-groups=\"filteredRootGroups\"\n" +
	"            placeholder=\"'SETTINGS_CONNECTIONS.FIELD_PLACEHOLDER_FILTER' | translate\"\n" +
	"            connection-properties=\"filteredConnectionProperties\"\n" +
	"            connection-group-properties=\"filteredConnectionGroupProperties\"></guac-group-list-filter>\n" +
	"\n" +
	"    </div>\n" +
	"\n" +
	"    <!-- List of accessible connections and groups -->\n" +
	"    <div class=\"connection-list\">\n" +
	"        <guac-group-list\n" +
	"            page-size=\"25\"\n" +
	"            connection-groups=\"filteredRootGroups\"\n" +
	"            connection-template=\"'app/settings/templates/connection.html'\"\n" +
	"            connection-group-template=\"'app/settings/templates/connectionGroup.html'\"/>\n" +
	"    </div>\n" +
	"</div>");
	$templateCache.put('app/settings/templates/settingsPreferences.html',
	"<div class=\"preferences\" ng-class=\"{loading: !isLoaded()}\">\n" +
	"    <!--\n" +
	"    Copyright 2015 Glyptodon LLC.\n" +
	"\n" +
	"    Permission is hereby granted, free of charge, to any person obtaining a copy\n" +
	"    of this software and associated documentation files (the \"Software\"), to deal\n" +
	"    in the Software without restriction, including without limitation the rights\n" +
	"    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n" +
	"    copies of the Software, and to permit persons to whom the Software is\n" +
	"    furnished to do so, subject to the following conditions:\n" +
	"\n" +
	"    The above copyright notice and this permission notice shall be included in\n" +
	"    all copies or substantial portions of the Software.\n" +
	"\n" +
	"    THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n" +
	"    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n" +
	"    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n" +
	"    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n" +
	"    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n" +
	"    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n" +
	"    THE SOFTWARE.\n" +
	"    -->\n" +
	"\n" +
	"    <!-- Language settings -->\n" +
	"    <div class=\"settings section language\">\n" +
	"        <p>{{'SETTINGS_PREFERENCES.HELP_LANGUAGE' | translate}}</p>\n" +
	"\n" +
	"        <!-- Language selection -->\n" +
	"        <div class=\"form\">\n" +
	"            <table class=\"fields\">\n" +
	"                <tr>\n" +
	"                    <th>{{'SETTINGS_PREFERENCES.FIELD_HEADER_LANGUAGE' | translate}}</th>\n" +
	"                    <td><select ng-model=\"preferences.language\" ng-change=\"changeLanguage()\" ng-options=\"key as name for (key, name) in languages | orderBy: name\"></select></td>\n" +
	"                </tr>\n" +
	"            </table>\n" +
	"        </div>\n" +
	"    </div>\n" +
	"    \n" +
	"    <!-- Password update -->\n" +
	"    <h2 class=\"header\" ng-show=\"canChangePassword\">{{'SETTINGS_PREFERENCES.SECTION_HEADER_UPDATE_PASSWORD' | translate}}</h2>\n" +
	"    <div class=\"settings section update-password\" ng-show=\"canChangePassword\">\n" +
	"        <p>{{'SETTINGS_PREFERENCES.HELP_UPDATE_PASSWORD' | translate}}</p>\n" +
	"\n" +
	"        <!-- Password editor -->\n" +
	"        <div class=\"form\">\n" +
	"            <table class=\"fields\">\n" +
	"                <tr>\n" +
	"                    <th>{{'SETTINGS_PREFERENCES.FIELD_HEADER_PASSWORD_OLD' | translate}}</th>\n" +
	"                    <td><input ng-model=\"oldPassword\" type=\"password\" /></td>\n" +
	"                </tr>\n" +
	"                <tr>\n" +
	"                    <th>{{'SETTINGS_PREFERENCES.FIELD_HEADER_PASSWORD_NEW' | translate}}</th>\n" +
	"                    <td><input ng-model=\"newPassword\" type=\"password\" /></td>\n" +
	"                </tr>\n" +
	"                <tr>\n" +
	"                    <th>{{'SETTINGS_PREFERENCES.FIELD_HEADER_PASSWORD_NEW_AGAIN' | translate}}</th>\n" +
	"                    <td><input ng-model=\"newPasswordMatch\" type=\"password\" /></td>\n" +
	"                </tr>\n" +
	"            </table>\n" +
	"        </div>\n" +
	"\n" +
	"        <!-- Form action buttons -->\n" +
	"        <div class=\"action-buttons\">\n" +
	"            <button class=\"change-password\" ng-click=\"updatePassword()\">{{'SETTINGS_PREFERENCES.ACTION_UPDATE_PASSWORD' | translate}}</button>\n" +
	"        </div>\n" +
	"    </div>\n" +
	"\n" +
	"    <!-- Input method -->\n" +
	"    <h2 class=\"header\">{{'SETTINGS_PREFERENCES.SECTION_HEADER_DEFAULT_INPUT_METHOD' | translate}}</h2>\n" +
	"    <div class=\"settings section input-method\">\n" +
	"        <p>{{'SETTINGS_PREFERENCES.HELP_DEFAULT_INPUT_METHOD' | translate}}</p>\n" +
	"        <div class=\"choices\">\n" +
	"\n" +
	"            <!-- No IME -->\n" +
	"            <div class=\"choice\">\n" +
	"                <label><input id=\"ime-none\" name=\"input-method\" ng-model=\"preferences.inputMethod\" type=\"radio\" value=\"none\"/> {{'SETTINGS_PREFERENCES.NAME_INPUT_METHOD_NONE' | translate}}</label>\n" +
	"                <p class=\"caption\"><label for=\"ime-none\">{{'SETTINGS_PREFERENCES.HELP_INPUT_METHOD_NONE' | translate}}</label></p>\n" +
	"            </div>\n" +
	"\n" +
	"            <!-- Text input -->\n" +
	"            <div class=\"choice\">\n" +
	"                <label><input id=\"ime-text\" name=\"input-method\" ng-model=\"preferences.inputMethod\" type=\"radio\" value=\"text\"/> {{'SETTINGS_PREFERENCES.NAME_INPUT_METHOD_TEXT' | translate}}</label>\n" +
	"                <p class=\"caption\"><label for=\"ime-text\">{{'SETTINGS_PREFERENCES.HELP_INPUT_METHOD_TEXT' | translate}} </label></p>\n" +
	"            </div>\n" +
	"\n" +
	"            <!-- Guac OSK -->\n" +
	"            <div class=\"choice\">\n" +
	"                <label><input id=\"ime-osk\" name=\"input-method\" ng-model=\"preferences.inputMethod\" type=\"radio\" value=\"osk\"/> {{'SETTINGS_PREFERENCES.NAME_INPUT_METHOD_OSK' | translate}}</label>\n" +
	"                <p class=\"caption\"><label for=\"ime-osk\">{{'SETTINGS_PREFERENCES.HELP_INPUT_METHOD_OSK' | translate}}</label></p>\n" +
	"            </div>\n" +
	"\n" +
	"        </div>\n" +
	"    </div>\n" +
	"\n" +
	"    <!-- Mouse mode -->\n" +
	"    <h2 class=\"header\">{{'SETTINGS_PREFERENCES.SECTION_HEADER_DEFAULT_MOUSE_MODE' | translate}}</h2>\n" +
	"    <div class=\"settings section mouse-mode\">\n" +
	"        <p>{{'SETTINGS_PREFERENCES.HELP_DEFAULT_MOUSE_MODE' | translate}}</p>\n" +
	"        <div class=\"choices\">\n" +
	"\n" +
	"            <!-- Touchscreen -->\n" +
	"            <div class=\"choice\">\n" +
	"                <input name=\"mouse-mode\" ng-model=\"preferences.emulateAbsoluteMouse\" type=\"radio\" ng-value=\"true\" checked=\"checked\" id=\"absolute\"/>\n" +
	"                <div class=\"figure\">\n" +
	"                    <label for=\"absolute\"><img src=\"images/settings/touchscreen.png\" alt=\"{{'SETTINGS_PREFERENCES.NAME_MOUSE_MODE_ABSOLUTE' | translate}}\"/></label>\n" +
	"                    <p class=\"caption\"><label for=\"absolute\">{{'SETTINGS_PREFERENCES.HELP_MOUSE_MODE_ABSOLUTE' | translate}}</label></p>\n" +
	"                </div>\n" +
	"            </div>\n" +
	"\n" +
	"            <!-- Touchpad -->\n" +
	"            <div class=\"choice\">\n" +
	"                <input name=\"mouse-mode\" ng-model=\"preferences.emulateAbsoluteMouse\" type=\"radio\" ng-value=\"false\" id=\"relative\"/>\n" +
	"                <div class=\"figure\">\n" +
	"                    <label for=\"relative\"><img src=\"images/settings/touchpad.png\" alt=\"{{'SETTINGS_PREFERENCES.NAME_MOUSE_MODE_RELATIVE' | translate}}\"/></label>\n" +
	"                    <p class=\"caption\"><label for=\"relative\">{{'SETTINGS_PREFERENCES.HELP_MOUSE_MODE_RELATIVE' | translate}}</label></p>\n" +
	"                </div>\n" +
	"            </div>\n" +
	"\n" +
	"        </div>\n" +
	"    </div>\n" +
	"\n" +
	"</div>");
	$templateCache.put('app/settings/templates/settingsSessions.html',
	"<div class=\"settings section sessions\" ng-class=\"{loading: !isLoaded()}\">\n" +
	"    <!--\n" +
	"    Copyright 2015 Glyptodon LLC.\n" +
	"\n" +
	"    Permission is hereby granted, free of charge, to any person obtaining a copy\n" +
	"    of this software and associated documentation files (the \"Software\"), to deal\n" +
	"    in the Software without restriction, including without limitation the rights\n" +
	"    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n" +
	"    copies of the Software, and to permit persons to whom the Software is\n" +
	"    furnished to do so, subject to the following conditions:\n" +
	"\n" +
	"    The above copyright notice and this permission notice shall be included in\n" +
	"    all copies or substantial portions of the Software.\n" +
	"\n" +
	"    THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n" +
	"    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n" +
	"    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n" +
	"    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n" +
	"    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n" +
	"    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n" +
	"    THE SOFTWARE.\n" +
	"    -->\n" +
	"\n" +
	"    <!-- User Session management -->\n" +
	"    <p>{{'SETTINGS_SESSIONS.HELP_SESSIONS' | translate}}</p>\n" +
	"\n" +
	"    <!-- Form action buttons -->\n" +
	"    <div class=\"action-buttons\">\n" +
	"        <button class=\"delete-sessions danger\" ng-disabled=\"!canDeleteSessions()\" ng-click=\"deleteSessions()\">{{'SETTINGS_SESSIONS.ACTION_DELETE' | translate}}</button>\n" +
	"    </div>\n" +
	"\n" +
	"    <!-- Session filter -->\n" +
	"    <guac-filter filtered-items=\"filteredWrappers\" items=\"wrappers\"\n" +
	"                 placeholder=\"'SETTINGS_SESSIONS.FIELD_PLACEHOLDER_FILTER' | translate\"\n" +
	"                 properties=\"filteredWrapperProperties\"></guac-filter>\n" +
	"\n" +
	"    <!-- List of current user sessions -->\n" +
	"    <table class=\"sorted session-list\">\n" +
	"        <thead>\n" +
	"            <tr>\n" +
	"                <th class=\"select-session\"></th>\n" +
	"                <th guac-sort-order=\"wrapperOrder\" guac-sort-property=\"'activeConnection.username'\">\n" +
	"                    {{'SETTINGS_SESSIONS.TABLE_HEADER_SESSION_USERNAME' | translate}}\n" +
	"                </th>\n" +
	"                <th guac-sort-order=\"wrapperOrder\" guac-sort-property=\"'startDate'\">\n" +
	"                    {{'SETTINGS_SESSIONS.TABLE_HEADER_SESSION_STARTDATE' | translate}}\n" +
	"                </th>\n" +
	"                <th guac-sort-order=\"wrapperOrder\" guac-sort-property=\"'activeConnection.remoteHost'\">\n" +
	"                    {{'SETTINGS_SESSIONS.TABLE_HEADER_SESSION_REMOTEHOST' | translate}}\n" +
	"                </th>\n" +
	"                <th guac-sort-order=\"wrapperOrder\" guac-sort-property=\"'name'\">\n" +
	"                    {{'SETTINGS_SESSIONS.TABLE_HEADER_SESSION_CONNECTION_NAME' | translate}}\n" +
	"                </th>\n" +
	"            </tr>\n" +
	"        </thead>\n" +
	"        <tbody>\n" +
	"            <tr ng-repeat=\"wrapper in wrapperPage\" class=\"session\">\n" +
	"                <td class=\"select-session\">\n" +
	"                    <input ng-change=\"wrapperSelectionChange(wrapper)\" type=\"checkbox\" ng-model=\"wrapper.checked\" />\n" +
	"                </td>\n" +
	"                <td>{{wrapper.activeConnection.username}}</td>\n" +
	"                <td>{{wrapper.startDate}}</td>\n" +
	"                <td>{{wrapper.activeConnection.remoteHost}}</td>\n" +
	"                <td>{{wrapper.name}}</td>\n" +
	"            </tr>\n" +
	"        </tbody>\n" +
	"    </table>\n" +
	"\n" +
	"    <!-- Text displayed if no sessions exist -->\n" +
	"    <p class=\"placeholder\" ng-hide=\"wrapperPage.length\">\n" +
	"        {{'SETTINGS_SESSIONS.INFO_NO_SESSIONS' | translate}}\n" +
	"    </p>\n" +
	"\n" +
	"    <!-- Pager for session list -->\n" +
	"    <guac-pager page=\"wrapperPage\" page-size=\"25\"\n" +
	"                items=\"filteredWrappers | orderBy : wrapperOrder.predicate\"></guac-pager>\n" +
	"</div>");
	$templateCache.put('app/settings/templates/settingsUsers.html',
	"<div class=\"settings section users\" ng-class=\"{loading: !isLoaded()}\">\n" +
	"    <!--\n" +
	"    Copyright 2015 Glyptodon LLC.\n" +
	"\n" +
	"    Permission is hereby granted, free of charge, to any person obtaining a copy\n" +
	"    of this software and associated documentation files (the \"Software\"), to deal\n" +
	"    in the Software without restriction, including without limitation the rights\n" +
	"    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n" +
	"    copies of the Software, and to permit persons to whom the Software is\n" +
	"    furnished to do so, subject to the following conditions:\n" +
	"\n" +
	"    The above copyright notice and this permission notice shall be included in\n" +
	"    all copies or substantial portions of the Software.\n" +
	"\n" +
	"    THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n" +
	"    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n" +
	"    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n" +
	"    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n" +
	"    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n" +
	"    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n" +
	"    THE SOFTWARE.\n" +
	"    -->\n" +
	"\n" +
	"    <!-- User management -->\n" +
	"    <p>{{'SETTINGS_USERS.HELP_USERS' | translate}}</p>\n" +
	"\n" +
	"\n" +
	"    <!-- User management toolbar -->\n" +
	"    <div class=\"toolbar\">\n" +
	"\n" +
	"        <!-- Form action buttons -->\n" +
	"        <div class=\"action-buttons\">\n" +
	"            <a class=\"add-user button\" ng-show=\"canCreateUsers()\"\n" +
	"               href=\"#/manage/{{getDefaultDataSource()}}/users/\">{{'SETTINGS_USERS.ACTION_NEW_USER' | translate}}</a>\n" +
	"        </div>\n" +
	"\n" +
	"        <!-- User filter -->\n" +
	"        <guac-filter filtered-items=\"filteredManageableUsers\" items=\"manageableUsers\"\n" +
	"                     placeholder=\"'SETTINGS_USERS.FIELD_PLACEHOLDER_FILTER' | translate\"\n" +
	"                     properties=\"filteredUserProperties\"></guac-filter>\n" +
	"\n" +
	"    </div>\n" +
	"\n" +
	"    <!-- List of users this user has access to -->\n" +
	"    <div class=\"user-list\">\n" +
	"        <div ng-repeat=\"manageableUser in manageableUserPage\" class=\"user list-item\">\n" +
	"            <a ng-href=\"#/manage/{{manageableUser.dataSource}}/users/{{manageableUser.user.username}}\">\n" +
	"                <div class=\"caption\">\n" +
	"                    <div class=\"icon user\"></div>\n" +
	"                    <span class=\"name\">{{manageableUser.user.username}}</span>\n" +
	"                </div>\n" +
	"            </a>\n" +
	"        </div>\n" +
	"    </div>\n" +
	"\n" +
	"    <!-- Pager controls for user list -->\n" +
	"    <guac-pager page=\"manageableUserPage\" page-size=\"25\"\n" +
	"                items=\"filteredManageableUsers | orderBy : 'user.username'\"></guac-pager>\n" +
	"\n" +
	"</div>");
	$templateCache.put('app/textInput/templates/guacKey.html',
	"<button class=\"key\" ng-click=\"updateKey()\" ng-class=\"{pressed: pressed, sticky: sticky}\">\n" +
	"    <!--\n" +
	"       Copyright (C) 2014 Glyptodon LLC\n" +
	"\n" +
	"       Permission is hereby granted, free of charge, to any person obtaining a copy\n" +
	"       of this software and associated documentation files (the \"Software\"), to deal\n" +
	"       in the Software without restriction, including without limitation the rights\n" +
	"       to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n" +
	"       copies of the Software, and to permit persons to whom the Software is\n" +
	"       furnished to do so, subject to the following conditions:\n" +
	"\n" +
	"       The above copyright notice and this permission notice shall be included in\n" +
	"       all copies or substantial portions of the Software.\n" +
	"\n" +
	"       THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n" +
	"       IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n" +
	"       FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n" +
	"       AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n" +
	"       LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n" +
	"       OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n" +
	"       THE SOFTWARE.\n" +
	"    -->\n" +
	"\n" +
	"    {{text | translate}}\n" +
	"</button>");
	$templateCache.put('app/textInput/templates/guacTextInput.html',
	"<div class=\"text-input\">\n" +
	"    <!--\n" +
	"       Copyright (C) 2014 Glyptodon LLC\n" +
	"\n" +
	"       Permission is hereby granted, free of charge, to any person obtaining a copy\n" +
	"       of this software and associated documentation files (the \"Software\"), to deal\n" +
	"       in the Software without restriction, including without limitation the rights\n" +
	"       to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n" +
	"       copies of the Software, and to permit persons to whom the Software is\n" +
	"       furnished to do so, subject to the following conditions:\n" +
	"\n" +
	"       The above copyright notice and this permission notice shall be included in\n" +
	"       all copies or substantial portions of the Software.\n" +
	"\n" +
	"       THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n" +
	"       IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n" +
	"       FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n" +
	"       AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n" +
	"       LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n" +
	"       OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n" +
	"       THE SOFTWARE.\n" +
	"    -->\n" +
	"\n" +
	"    <!-- Text input target -->\n" +
	"    <div class=\"text-input-field\"><div class=\"sent-history\"><div class=\"sent-text\" ng-repeat=\"text in sentText track by $index\">{{text}}</div></div><textarea rows=\"1\" class=\"target\" autocorrect=\"off\" autocapitalize=\"off\"></textarea></div><div class=\"text-input-buttons\"><guac-key keysym=\"65507\" sticky=\"true\" text=\"'CLIENT.NAME_KEY_CTRL'\" pressed=\"ctrlPressed\"></guac-key><guac-key keysym=\"65513\" sticky=\"true\" text=\"'CLIENT.NAME_KEY_ALT'\" pressed=\"altPressed\"></guac-key><guac-key keysym=\"65307\" text=\"'CLIENT.NAME_KEY_ESC'\"></guac-key><guac-key keysym=\"65289\" text=\"'CLIENT.NAME_KEY_TAB'\"></guac-key></div>\n" +
	"\n" +
	"</div>");
}]);
