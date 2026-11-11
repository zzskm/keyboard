#include QMK_KEYBOARD_H

enum layers { BASE, NUM, SYM, NAV };

// Within each half: plate rows from back to front, then switches from drawing
// left to right. The right cross is ordered left, up, down, right.
const uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {
    [BASE] = LAYOUT(
        KC_Q,        KC_W,        KC_E,    KC_R,    KC_T,    KC_Y,
        KC_A,        KC_S,        KC_D,    KC_F,    KC_G,    KC_H,
        SFT_T(KC_Z), ALT_T(KC_X), KC_C,    KC_V,    KC_B,    KC_N,
        KC_ESC,      KC_TAB,      KC_LCTL,

        KC_U,        KC_I,        KC_O,    KC_P,    KC_BSPC, KC_PGUP,
        KC_J,        KC_K,        KC_L,    KC_SCLN, KC_QUOT, KC_PGDN,
        KC_M,        KC_COMM,     KC_DOT,  SFT_T(KC_SLSH),   KC_UP,
        KC_LGUI,     LT(NUM, KC_BSPC),     LT(SYM, KC_SPC),
        KC_LEFT,     MO(NAV),     KC_DOWN, KC_RGHT
    ),
    [NUM] = LAYOUT(
        KC_1,        KC_2,        KC_3,    KC_4,    KC_5,    KC_6,
        _______,     _______,     _______, _______, _______, _______,
        KC_LSFT,     KC_LALT,     _______, _______, _______, _______,
        _______,     _______,     _______,

        KC_7,        KC_8,        KC_9,    KC_0,    KC_DEL,  KC_HOME,
        _______,     _______,     _______, _______, _______, KC_END,
        _______,     _______,     _______, _______, _______,
        _______,     _______,     KC_ENT,
        _______,     _______,     _______, _______
    ),
    [SYM] = LAYOUT(
        KC_EXLM,     KC_AT,       KC_HASH, KC_DLR,  KC_PERC, KC_CIRC,
        _______,     _______,     _______, _______, KC_GRV,  KC_MINS,
        KC_LSFT,     KC_LALT,     _______, _______, KC_TILD, KC_UNDS,
        _______,     _______,     _______,

        KC_AMPR,     KC_ASTR,     KC_LPRN, KC_RPRN, _______, _______,
        KC_EQL,      KC_LBRC,     KC_RBRC, KC_BSLS, _______, _______,
        KC_PLUS,     KC_LCBR,     KC_RCBR, KC_PIPE, _______,
        _______,     KC_ENT,      _______,
        _______,     _______,     _______, _______
    ),
    [NAV] = LAYOUT(
        KC_F1,       KC_F2,       KC_F3,   KC_F4,   KC_F5,   KC_F6,
        KC_F7,       KC_F8,       KC_F9,   KC_F10,  KC_F11,  KC_F12,
        KC_LSFT,     KC_LALT,     _______, _______, _______, _______,
        _______,     _______,     _______,

        _______,     _______,     _______, _______, KC_DEL,  KC_HOME,
        _______,     _______,     _______, _______, _______, KC_END,
        _______,     _______,     _______, _______, KC_PGUP,
        _______,     KC_DEL,      KC_ENT,
        KC_HOME,     _______,     KC_PGDN, KC_END
    ),
};
