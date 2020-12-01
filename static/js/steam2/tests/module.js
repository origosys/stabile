dojo.provide("steam2.tests.module");

try{
	dojo.require("steam2.tests.testStores");
	dojo.require("steam2.dialogs.tests.testServerDialog");
	dojo.require("steam2.models.tests.testServer");
	dojo.require("steam2.tests.testServersGrid");

	doh.registerUrl("steam2.tests.testServersGrid", dojo.moduleUrl("steam2","tests/testServersGrid.html"));
	doh.registerUrl("steam2.tests.testFilteringSelectWithDeselect", dojo.moduleUrl("steam2","tests/testFilteringSelectWithDeselect.html"));

}catch(e){
	doh.debug(e);
}



