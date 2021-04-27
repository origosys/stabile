#!/usr/bin/php5

<?php
error_reporting(0); // Set E_ALL for debuging

include_once dirname(__FILE__).DIRECTORY_SEPARATOR.'elFinderConnector.class.php';
include_once dirname(__FILE__).DIRECTORY_SEPARATOR.'elFinder.class.php';
include_once dirname(__FILE__).DIRECTORY_SEPARATOR.'elFinderVolumeDriver.class.php';
include_once dirname(__FILE__).DIRECTORY_SEPARATOR.'elFinderVolumeLocalFileSystem.class.php';
// Required for MySQL storage connector
// include_once dirname(__FILE__).DIRECTORY_SEPARATOR.'elFinderVolumeMySQL.class.php';
// Required for FTP connector support
include_once dirname(__FILE__).DIRECTORY_SEPARATOR.'elFinderVolumeFTP.class.php';

if ($_SERVER['REQUEST_METHOD'] == 'POST') {
    if (strpos($_SERVER[CONTENT_TYPE], "multipart/form-data") === false) {
//      parse_str(trim(fgets(STDIN)));
        parse_str(stream_get_contents(STDIN), $_POST);
    } else {
        parseMulti();
    }
    parse_str($_SERVER['QUERY_STRING'], $_GET);
} else {
    parse_str($_SERVER['QUERY_STRING'], $_GET);
}

/**
 * Simple function to demonstrate how to control file access using "accessControl" callback.
 * This method will disable accessing files/folders starting from  '.' (dot)
 *
 * @param  string  $attr  attribute name (read|write|locked|hidden)
 * @param  string  $path  file path relative to volume root directory started with directory separator
 * @return bool|null
 **/
function access($attr, $path, $data, $volume) {
	return strpos(basename($path), '.') === 0       // if file/folder begins with '.' (dot)
		? !($attr == 'read' || $attr == 'write')    // set read+write to false, other (locked+hidden) set to true
		:null;                                    // else elFinder decide it itself
}

function accessRO($attr, $path, $data, $volume) {
    if (strpos(basename($path), '.') === 0) {
    	return !($attr == 'read' || $attr == 'write');
    } else {
        return !($attr == 'write' || $attr == 'hidden');
    }
}

$roots = array();

// Parse cookies
$cookiesTxt = (isset($_SERVER['HTTP_COOKIE'])) ? $_SERVER['HTTP_COOKIE'] : '';
$cookiesPairs = explode("; ", $cookiesTxt);
$cookiesHash = array();
foreach ($cookiesPairs as $i => $pair) {
    if($pair === ''){continue;}
    $parts = explode('=', $pair);
    if (isset($parts[1])) {
      $cookiesHash[ $parts[0] ] = $parts[1];
    }
};

// Get the auth_tkt token
if (isset($cookiesHash['auth_tkt']) && !($cookiesHash['auth_tkt']==='')) {
    $tkt = urldecode($cookiesHash['auth_tkt']);
    $cmd = '/usr/local/bin/ticketmaster.pl ' . escapeshellarg($tkt) . '  --dir';
    $tktdata = explode("\n", `$cmd` );
    $tktuser = $tktdata[0];
    $tktdir = "/mnt/data/" . $tktdata[1];
//    $tktuser = exec('/usr/local/bin/ticketmaster.pl '.escapeshellarg($tkt));
}

if (session_id()==='' && isset($tkt) && $tkt!=='') { // We don't have a PHP session, make a new one
    $sid = session_id(strtolower( substr( $tkt, 0, 26 )));
};
session_start();
$session_id = session_id();
if ($session_id === '') { // Something went wrong, we don't have a session
    file_put_contents("/tmp/SESSION_error.txt", 'error');
} else {
//    file_put_contents("/tmp/SESSION_$session_id.txt", $session_id);
}

$invalid = isInvalid($tktuser);

if (isset($tktuser) && $tktuser!=='' && $tktuser!=='g' && !$invalid) {
    if (file_exists("/mnt/data/users/$tktuser")) {
        array_push($roots,
            array(
                'alias'         => 'Home',
                'driver'        => 'LocalFileSystem',   // driver for accessing file system (REQUIRED)
                'path'          => "/mnt/data/users/$tktuser",         // path to files (REQUIRED)
                'accessControl' => 'access',             // disable and hide dot starting files (OPTIONAL)
                'uploadMaxSize' => '100M',
                'URL'           => "../../users/$tktuser" // URL to files (REQUIRED)
            )
        );
    }
}

if ((isset( $_GET ) && isset($_GET['nfs'])) || (isset( $_POST ) && isset($_POST['nfs']))) {
    $nfsid = '0';
    if (isset( $_POST ) && isset($_POST['nfs'])) $nfsid = $_POST['nfs'];
    else $nfsid = $_GET['nfs'];

    array_push($roots,
        array(
            'driver'        => 'LocalFileSystem',   // driver for accessing file system (REQUIRED)
            'path'          => "../fuel/$nfsid",         // path to files (REQUIRED)
            'accessControl' => 'access',             // disable and hide dot starting files (OPTIONAL)
            'uploadMaxSize' => '100M',
            'URL'           => "fuel/$nfsid" // URL to files (REQUIRED)
        )
    );
} elseif (isset($tktuser) && $tktuser!=='' && $tktuser!=='g' && !$invalid && file_exists("/mnt/data/shared")) {
    array_push($roots,
        array(
            'alias'         => 'Shared',
            'driver'        => 'LocalFileSystem',   // driver for accessing file system (REQUIRED)
            'path'          => '/mnt/data/shared/',         // path to files (REQUIRED)
            'accessControl' => (isWriter($tktuser)) ? 'access':'accessRO',
            'uploadMaxSize' => '100M',
            'URL'           => '../../shared/' // URL to files (REQUIRED)
        )
    );
} elseif (isset($tktuser) && $tktuser=='g') {
    array_push($roots,
        array(
            'driver'        => 'LocalFileSystem',   // driver for accessing file system (REQUIRED)
            'path'          => $tktdir,
            'disabled'      => array('mkfile', 'archive', 'mkdir', 'btsync', 'remove', 'info'),
            'accessControl' => 'accessRO'
        )
    );
} elseif (file_exists("../../files")) {
    array_push($roots,
        array(
            'driver'        => 'LocalFileSystem',   // driver for accessing file system (REQUIRED)
            'path'          => '../../files',         // path to files (REQUIRED)
            'disabled'      => array('smbmount', 'btsync'),
            'accessControl' => 'access',             // disable and hide dot starting files (OPTIONAL)
            'uploadMaxSize' => '100M',
            'URL'           => 'files/' // URL to files (REQUIRED)
        )
    );
}

if (isset($tktuser) && $tktuser!=='' && $tktuser!=='g') {
    $intip = `cat /tmp/internalip`;
    if (file_exists('/etc/origo/internalip')) {
        $intip = `cat /etc/origo/internalip`;
    }
    $dominfo = `samba-tool domain info $intip`;
    preg_match('/Domain\s+: (\S+)/', $dominfo, $matches);
    $sambadomain = $matches[1];
    $domparts = explode(".", $sambadomain);
    $userbase = "CN=users,DC=" . implode(",DC=", $domparts);

    $cmd = "/usr/bin/ldbsearch -H /opt/samba4/private/sam.ldb -b \"CN=$tktuser,$userbase\" objectClass=user memberof";
    $res = `$cmd`;
    $lines = explode("\n", $res);
    foreach ($lines as $line) {
        preg_match('/^memberOf: CN=(.+),CN=Users/', $line, $matches);
        if ($matches[1]) {
            $group = $matches[1];
            if (file_exists("/mnt/data/groups/$group")) {
                array_push($roots,
                    array(
                        'driver'        => 'LocalFileSystem',   // driver for accessing file system (REQUIRED)
                        'path'          => "/mnt/data/groups/$group",         // path to files (REQUIRED)
                        'accessControl' => (isWriter($tktuser, $group)) ? 'access':'accessRO',
                        'uploadMaxSize' => '100M',
                        'URL'           => "../../groups/$group" // URL to files (REQUIRED)
                    )
                );
            }
        }
    };
}

$opts = array(
	//'debug' => true,
    'PHPSESSID' => $session_id,
	'roots' => $roots
);

//echo "Content-type: text/html\n\n$path :: $tktdata[0] \n";
// run elFinder
$connector = new elFinderConnector(new elFinder($opts));
$connector->run();

///////////////////

function isWriter($tktuser, $group) {
    $conf = "/etc/samba/smb.conf";
    if ($group) {
		$conf = "/etc/samba/smb.conf.group.$group";
	};
    if (file_exists($conf)) {
        $wlist = `cat "$conf" | grep "write list"`;
        $wlist = chop($wlist);
        if (preg_match('/write list =(.+)/', $wlist, $matches)) {
            $wlist = $matches[1];
            preg_match_all('/\+?"(?:\\\\.|[^\\\\"])*"|\S+/', $wlist, $writers);
            foreach ($writers[0] as $writer) {
                if (preg_match('/(\+)?"(.+)\\\\(.+)"/', $writer, $m)) {
                    if ($m[1] == '+') {
                        if (isGroupMember($tktuser, $m[3])) {return TRUE;}
                    } else {
                        $writer = $m[3];
                        if (strtolower($writer) == strtolower($tktuser)) {return TRUE;}
                    }
                }
            }
        } else {
            return TRUE; // No write list
        }
    }
}

function isInvalid($tktuser) {
    $conf = "/etc/samba/smb.conf";
    if (file_exists($conf)) {
        $wlist = `cat "$conf" | grep "invalid users"`;
        $wlist = chop($wlist);
        if (preg_match('/invalid users =(.+)/', $wlist, $matches)) {
            $wlist = $matches[1];
            preg_match_all('/\+?"(?:\\\\.|[^\\\\"])*"|\S+/', $wlist, $writers);
            foreach ($writers[0] as $writer) {
                if (preg_match('/(\+)?"(.+)\\\\(.+)"/', $writer, $m)) {
                    if ($m[1] == '+') {
                        if (isGroupMember($tktuser, $m[3])) {return TRUE;}
                    } else {
                        $writer = $m[3];
                        if (strtolower($writer) == strtolower($tktuser)) {return TRUE;}
                    }
                }
            }
        }
    }
    return FALSE;// No invalid users
}

function isGroupMember($tktuser, $group) {
    $glist = `samba-tool group listmembers "$group"`;
    $groups = explode("\n", $glist);
    foreach ($groups as $g) {
        if (strtolower($g) == strtolower($tktuser)) {return TRUE;}
    }
}

// One method for parsing multi-part: http://stackoverflow.com/questions/9464935/php-multipart-form-data-put-request

function parseMulti(  )
{
    global $_POST;
    global $_FILES;

    /* PUT data comes in on the stdin stream */
//    $putdata = fopen("php://input", "r");
    $putdata = STDIN;

    /* Open a file for writing */
    // $fp = fopen("myputfile.ext", "w");

    $raw_data = '';

    /* Read the data 1 KB at a time
       and write to the file */
    while ($chunk = fread($putdata, 1024))
        $raw_data .= $chunk;

    /* Close the streams */
    fclose($putdata);

    // Fetch content and determine boundary
    $boundary = substr($raw_data, 0, strpos($raw_data, "\r\n"));

    if(empty($boundary)){
        parse_str($raw_data,$data);
        $GLOBALS[ '_POST' ] = $data;
        return;
    }

    // Fetch each part
    $parts = array_slice(explode($boundary, $raw_data), 1);
    $data = array();

    foreach ($parts as $part) {
        // If this is the last part, break
        if ($part == "--\r\n") break;

        // Separate content from headers
        $part = ltrim($part, "\r\n");
        list($raw_headers, $body) = explode("\r\n\r\n", $part, 2);

        // Parse the headers list
        $raw_headers = explode("\r\n", $raw_headers);
        $headers = array();
        foreach ($raw_headers as $header) {
            list($name, $value) = explode(':', $header);
            $headers[strtolower($name)] = ltrim($value, ' ');
        }

        // Parse the Content-Disposition to get the field name, etc.
        if (isset($headers['content-disposition'])) {
            $filename = null;
            $tmp_name = null;
            preg_match(
                '/^(.+); *name="([^"]+)"(; *filename="([^"]+)")?/',
                $headers['content-disposition'],
                $matches
            );
            list(, $type, $name) = $matches;

            //Parse File
            if( isset($matches[4]) )
            {
                //if labeled the same as previous, skip
                if( isset( $_FILES[ $matches[ 2 ] ] ) )
                {
                    continue;
                }

                //get filename
                $filename = $matches[4];

                //get tmp name
                $filename_parts = pathinfo( $filename );
                $tmp_name = tempnam( ini_get('upload_tmp_dir'), $filename_parts['filename']);

                //populate $_FILES with information, size may be off in multibyte situation
                $match = $matches[ 2 ];
                if ($match == 'upload[]') $match='upload';
                $_FILES[ $match ] = array(
                    'error'=>array(0),
                    'name'=>array($filename),
                    'tmp_name'=>array($tmp_name),
                    'size'=>array(strlen( $body )),
                    'type'=>array($value)
                );

                //place in temporary directory
                file_put_contents($tmp_name, $body);
            }
            //Parse Field
            else
            {
                $data[$name] = substr($body, 0, strlen($body) - 2);
            }
        }

    }
    $GLOBALS[ '_POST' ] = $data;
    return;
}

// Another method: http://throwachair.com/2013/09/09/php-parsing-multipartform-data-the-correct-way-when-using-non-post-methods

function HttpParseHeaderValue($line) {
    $retval = array();
    $regex  = <<<'EOD'
                /
            (?:^|;)\s*
                (?[^=,;\s"]*)
                (?:
                    (?:="
                        (?[^"\\]*(?:\\.[^"\\]*)*)
                        ")
                    |(?:=(?[^=,;\s"]*))
                )?
                /mx
EOD;

    $matches = null;
    preg_match_all($regex, $line, $matches, PREG_SET_ORDER);

    for($i = 0; $i < count($matches); $i++) {
        $match = $matches[$i];
        $name = $match['name'];
        $quotedValue = $match['quotedValue'];
        if(empty($quotedValue)) {
            $value = $match['value'];
        } else {
            $value = stripcslashes($quotedValue);
        }
        if(empty($value) && $i == 0) {
            $value = $name;
            $name = 'value';
        }
        $retval[$name] = $value;
    }
    return $retval;
}

function HttpParseMultipart($stream, $boundary, array &$variables, array &$files) {
     if($stream == null) {
         $stream = fopen('php://input');
     }
 
     $partInfo = null;
 
     $lineN = fgets($stream);
     while(($lineN = fgets($stream)) !== false) {
         if(strpos($lineN, '--') === 0) {
             if(!isset($boundary)) {
                 $boundary = rtrim($lineN);
             }
             continue;
         }
 
         $line = rtrim($lineN);
 
         if($line == '') {
             if(!empty($partInfo['Content-Disposition']['filename'])) {
                 HttpParseMultipartFile($stream, $boundary, $partInfo, $files);
             } else {
                 HttpParseMultipartVariable($stream, $boundary, $partInfo['Content-Disposition']['name'], $variables);
             }
             $partInfo = null;
             continue;
         }
 
         $delim = strpos($line, ':');
 
         $headerKey = substr($line, 0, $delim);
         $headerVal = ltrim(substr($line, $delim + 1));
         $partInfo[$headerKey] = HttpParseHeaderValue($headerVal);
     }
     fclose($stream);
 }
 
 function HttpParseMultipartVariable($stream, $boundary, $name, &$array) {
     $fullValue = '';
     $lastLine = null;
     while(($lineN = fgets($stream)) !== false && strpos($lineN, $boundary) !== 0) {
         if($lastLine != null) {
             $fullValue .= $lastLine;
         }
         $lastLine = $lineN;
     }
 
     if($lastLine != null) {
         $fullValue .= rtrim($lastLine, "\r\n");
     }
 
     $array[$name] = $fullValue;
 }
 
 function HttpParseMultipartFile($stream, $boundary, $info, &$array) {
     $tempdir = sys_get_temp_dir();
     // we should technically 'clean' name - replace '.' with _, etc
     // http://stackoverflow.com/questions/68651/get-php-to-stop-replacing-characters-in-get-or-post-arrays
     $name = $info['Content-Disposition']['name'];
     $fileStruct['name'] = $info['Content-Disposition']['filename'];
     $fileStruct['type'] = $info['Content-Type']['value'];
 
     $array[$name] = &$fileStruct;
 
     if(empty($tempdir)) {
         $fileStruct['error'] = UPLOAD_ERR_NO_TMP_DIR;
         return;
     }
 
     $tempname = tempnam($tempdir, 'php');
     $outFP = fopen($tempname, 'wb');
 
     $fileStruct['tmp_name'] = $tempname;
     if($outFP === false) {
         $fileStruct['error'] = UPLOAD_ERR_CANT_WRITE;
         return;
     }
 
     $lastLine = null;
     while(($lineN = fgets($stream, 8096)) !== false && strpos($lineN, $boundary) !== 0) {
         if($lastLine != null) {
             if(fwrite($outFP, $lastLine) === false) {
                 $fileStruct['error'] = UPLOAD_ERR_CANT_WRITE;
                 return;
             }
         }
         $lastLine = $lineN;
     }
 
     if($lastLine != null) {
         if(fwrite($outFP, rtrim($lastLine, "\r\n")) === false) {
                 $fileStruct['error'] = UPLOAD_ERR_CANT_WRITE;
                 return;
         }
     }
     $fileStruct['error'] = UPLOAD_ERR_OK;
     $fileStruct['size'] = filesize($tempname);
 }

?>
