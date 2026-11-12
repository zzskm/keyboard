#include QMK_KEYBOARD_H

// Ported from 46es/firmware/46es_kbfirmware.json (layers 0-3) by physical
// position. The 46es matrix rows are wiring rows; here every row is a physical
// row from back to front, left half then right half.
//   Left:  rows of 6, 6, 5 (no outer key on row 3), then 3 thumbs.
//   Right: rows of 7, 7, 5, then 3 thumbs, then the cross (left, up, down, right).

enum layers { BASE, NUM, SYM, FN };

const uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {
    [BASE] = LAYOUT(
        KC_ESC,  KC_Q,        KC_W,        KC_E,    KC_R,    KC_T,
        KC_TAB,  KC_A,        KC_S,        KC_D,    KC_F,    KC_G,
                 SFT_T(KC_Z), ALT_T(KC_X), KC_C,    KC_V,    KC_B,
                 KC_LCTL,     KC_LGUI,     LT(NUM, KC_SPC),

        KC_Y,    KC_U,        KC_I,        KC_O,    KC_P,    KC_BSPC, KC_PGUP,
        KC_H,    KC_J,        KC_K,        KC_L,    KC_SCLN, KC_QUOT, KC_PGDN,
        KC_N,    KC_M,        KC_COMM,     KC_DOT,  SFT_T(KC_SLSH),
        LT(SYM, KC_SPC),      KC_RALT,     MO(FN),
        KC_LEFT, KC_UP,       KC_DOWN,     KC_RGHT
    ),
    [NUM] = LAYOUT(
        _______, KC_1,        KC_2,        KC_3,    KC_4,    KC_5,
        _______, XXXXXXX,     XXXXXXX,     XXXXXXX, XXXXXXX, XXXXXXX,
                 KC_LSFT,     KC_LALT,     XXXXXXX, XXXXXXX, XXXXXXX,
                 _______,     _______,     KC_ENT,

        KC_6,    KC_7,        KC_8,        KC_9,    KC_0,    _______, KC_HOME,
        XXXXXXX, XXXXXXX,     XXXXXXX,     XXXXXXX, XXXXXXX, _______, KC_END,
        XXXXXXX, XXXXXXX,     XXXXXXX,     XXXXXXX, XXXXXXX,
        KC_ENT,               _______,     _______,
        _______, _______,     _______,     _______
    ),
    [SYM] = LAYOUT(
        _______, KC_EXLM,     KC_AT,       KC_HASH, KC_DLR,  KC_PERC,
        _______, XXXXXXX,     XXXXXXX,     XXXXXXX, XXXXXXX, KC_GRV,
                 KC_LSFT,     KC_LALT,     XXXXXXX, XXXXXXX, KC_TILD,
                 _______,     _______,     KC_ENT,

        KC_CIRC, KC_AMPR,     KC_ASTR,     KC_LPRN, KC_RPRN, _______, KC_HOME,
        KC_MINS, KC_EQL,      KC_LBRC,     KC_RBRC, KC_BSLS, _______, KC_END,
        KC_UNDS, KC_PLUS,     KC_LCBR,     KC_RCBR, KC_PIPE,
        KC_ENT,               _______,     _______,
        _______, _______,     _______,     _______
    ),
    [FN] = LAYOUT(
        LSG(KC_S), KC_F1,     KC_F2,       KC_F3,   KC_F4,   KC_F5,
        XXXXXXX, KC_F6,       KC_F7,       KC_F8,   KC_F9,   KC_F10,
                 KC_F11,      KC_F12,      KC_F13,  KC_F14,  KC_F15,
                 _______,     _______,     KC_DEL,

        QK_BOOT, XXXXXXX,     XXXXXXX,     XXXXXXX, XXXXXXX, XXXXXXX, KC_VOLU,
        XXXXXXX, XXXXXXX,     XXXXXXX,     XXXXXXX, XXXXXXX, XXXXXXX, KC_VOLD,
        XXXXXXX, XXXXXXX,     XXXXXXX,     XXXXXXX, XXXXXXX,
        KC_DEL,               _______,     _______,
        _______, _______,     _______,     _______
    ),
};
