// This file is loaded into the Kubernetes dashboard for simple logout functionality
window.addEventListener('load', function() {
    function addListener() {
        if (document.getElementsByClassName("mat-menu-trigger")[0]) {
            document.getElementsByClassName("mat-menu-trigger")[0].addEventListener('click', function() {
                document.getElementsByClassName("kd-auth-header")[0].innerHTML="<a href='https://log:out@" + location.host + "/'>log out</a>";
            });
        } else {
            setTimeout(function() {
                addListener();
            }, 1000);
        }
    };
    addListener();
})
