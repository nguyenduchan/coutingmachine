// Export wrappers — avoid PowerShell -D quoting issues
// Usage: openscad -o out.stl export_<part>.scad

module _load() {
    // override defaults by calling modules from parent via use
}

use <screw_rotary_feeder.scad>

// This file is a template; concrete exports below are separate files.
