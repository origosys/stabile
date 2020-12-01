#!/usr/bin/php5

<?php
echo "Content-Type: application/json\n\n";
error_reporting(0); // Set E_ALL for debuging

include_once dirname(__FILE__).DIRECTORY_SEPARATOR.'elFinderConnector.class.php';
include_once dirname(__FILE__).DIRECTORY_SEPARATOR.'elFinder.class.php';
include_once dirname(__FILE__).DIRECTORY_SEPARATOR.'elFinderVolumeDriver.class.php';
include_once dirname(__FILE__).DIRECTORY_SEPARATOR.'elFinderVolumeLocalFileSystem.class.php';
// Required for MySQL storage connector
// include_once dirname(__FILE__).DIRECTORY_SEPARATOR.'elFinderVolumeMySQL.class.php';
// Required for FTP connector support
// include_once dirname(__FILE__).DIRECTORY_SEPARATOR.'elFinderVolumeFTP.class.php';

if ($_SERVER['REQUEST_METHOD'] == 'POST') {
    if (strpos($_SERVER[CONTENT_TYPE], "multipart/form-data") === false) {
//      parse_str(trim(fgets(STDIN)));
        parse_str(stream_get_contents(STDIN), $_POST);
    } else {
        parseMulti();
    //    print_r($_POST);
    //    print_r($_FILES);
    //    exit;
    }
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
		:  null;                                    // else elFinder decide it itself
}

$opts = array(
	//'debug' => true,
	'roots' => array(
		array(
			'driver'        => 'LocalFileSystem',   // driver for accessing file system (REQUIRED)
			'path'          => '../files/',         // path to files (REQUIRED)
			'URL'           => '/elfinder/files/', // URL to files (REQUIRED)
			'accessControl' => 'access'             // disable and hide dot starting files (OPTIONAL)
		)
	)
);

// run elFinder
$connector = new elFinderConnector(new elFinder($opts));
$connector->run();



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