<?php
/**
 * This script will flush all files in this or a subdirectory from APC.
 */
 if($_SERVER['REMOTE_ADDR'] === '127.0.0.1') {
  $fileAbsPath = dirname(__FILE__);
  print_r($fileAbsPath);

  // APC can't flush whole directories directly by just giving the directory path.
  // Instead retrieve all matching cache entries using an ApcIterator.
  $quotedPath = preg_quote(rtrim($fileAbsPath, '/') . '/', '/');
  $iterator = new \APCIterator('file', '/^'. $quotedPath . '.*/');

  if (apc_delete_file($iterator)) {
    print_r($iterator);
    echo "Removed from APC", PHP_EOL;
  }
  else {
    echo "Not removed from APC", PHP_EOL;
  }
}
else {
  echo "Can only be run from localhost.";
}
