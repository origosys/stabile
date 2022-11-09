#!/bin/bash

if grep --quiet "HTTP_HOST" /usr/share/wordpress/wp-admin/install.php; then
	echo "Modifications already made"
else
	echo "Modifying WordPress files"

# Fix link to install.css
	perl -pi -e 's/(<\?php(\n)?\s+wp_admin_css\(.+install.+ true \);(\n)?\s+\?>)/<link rel="stylesheet" id="install-css"  href="css\/install\.css" type="text\/css" media="all" \/>/;' /usr/share/wordpress/wp-admin/install.php
  perl -pi -e 's/wp_admin_css\(.+install.+ true \);/echo "<link rel=\\"stylesheet\\" id=\\"install-css\\"  href=\\"css\/install\.css\\" type=\\"text\/css\\" media=\\"all\\" \/>";/g;' /usr/share/wordpress/wp-admin/install.php

# Make install page prettier in stabile configure dialog
	perl -pi -e 's/margin:2em auto/margin:0 auto/;' /usr/share/wordpress/wp-admin/css/install.css

# Redirect to Webmin when WordPress is installed
#	perl -pi -e 's/(<a href="\.\.\/wp-login\.php".+<\/a>)/<!-- $1 --><script>var pipeloc=location\.href\.substring(0,location.href.indexOf("\/home")); location=pipeloc \+ ":10000\/stabile\/?wp=<?php echo \$_SERVER[HTTP_HOST]; ?>";<\/script>/;' /usr/share/wordpress/wp-admin/install.php

# Replace button with link to login page with redirect to our app page
#  Old version
#    perl -pi -e 's/(<a href="\.\.\/wp-login\.php".+<\/a>)/<!-- $1 --><script>var pipeloc=location\.href\.substring(0,location.href.indexOf("\/home")); location=pipeloc \+ ":10000\/stabile\/?show=showdummy-site";<\/script>/;' /usr/share/wordpress/wp-admin/install.php
  perl -pi -e 's/(<a href=".+wp_login_url.+">.+<\/a>)/<!-- $1 --><script>var pipeloc=location\.href\.substring(0,location.href.indexOf("\/home")); location=pipeloc \+ ":10000\/stabile\/?show=showdummy-site";<\/script>/;' /usr/share/wordpress/wp-admin/install.php

  perl -pi -e "unless (\$match) {\$match = s/showdummy/' . \\\$showsite . '/;}" /usr/share/wordpress/wp-admin/install.php
  perl -pi -e 'if (!$match) {$match = s/showdummy/<?php echo \$showsite; ?>/;}' /usr/share/wordpress/wp-admin/install.php

  perl -pi -e 's/(\/\/ Sanity check\.)/$1\n\$showsite=( (preg_match("\/\\.\\w+\\.\\w+\$\/", \$_SERVER[HTTP_HOST], \$matches, PREG_OFFSET_CAPTURE)===FALSE )? "default" : substr(\$_SERVER[HTTP_HOST], 0, \$matches[0][1]) );\n/' /usr/share/wordpress/wp-admin/install.php

# Make link to virtual host work, even if not registered in DNS, by adding host=, which is interpreted by stabile proxy
  # perl -pi -e "s/(step=1)/\$1\&host=' . \\\$_SERVER[HTTP_HOST] .'/;" /usr/share/wordpress/wp-admin/install.php
  perl -pi -e 's/(action="install.php\?step=2)/$1&host=<?php echo \$_SERVER[HTTP_HOST]; ?>/;' /usr/share/wordpress/wp-admin/install.php
  perl -pi -e 's/(.* action="\?step=1".*)/            echo "<form id=setup method=post action=?step=1&host=\$_SERVER[HTTP_HOST]>";/;' /usr/share/wordpress/wp-admin/install.php

# Ask stabile to change the managementlink from Wordpress install page, so the above redirect is not needed on subsequent loads
  perl -pi -e 's/(if \( is_blog_installed\(\) \) \{)/$1\n    \`curl -k -X PUT --data-urlencode "PUTDATA={\\"uuid\\":\\"this\\",\\"managementlink\\":\\"\/stabile\/pipe\/http:\/\/{uuid}:10000\/stabile\/\\"}" https:\/\/10.0.0.1\/stabile\/images\`;/;' /usr/share/wordpress/wp-admin/install.php

# perl -pi -e 's/(<h1>.+Success!.+<\/h1>)/$1\n    <?php\n\`curl -k -X PUT --data-urlencode "PUTDATA={\\"uuid\\":\\"this\\",\\"managementlink\\":\\"\/stabile\/pipe\/http:\/\/{uuid}:10000\/stabile\/\\"}" https:\/\/10.0.0.1\/stabile\/images\`;\n    ?>/;' /usr/share/wordpress/wp-admin/install.php

# Make strength meter work in install page after upgrading WordPress
	perl -pi -e 's/(.+src.+ => )(empty.+),/$1\"\.\.\/wp-includes\/js\/zxcvbn\.min\.js\"/;' /usr/share/wordpress/wp-includes/script-loader.php
fi

# Allow root to log into mysql
  echo "UPDATE mysql.user SET plugin = '' WHERE user = 'root' AND host = 'localhost';" | mysql
  echo "FLUSH PRIVILEGES" | mysql
