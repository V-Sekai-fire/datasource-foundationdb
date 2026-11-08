/* picotls.h defines PTLS_BUILD_ASSERT_EXPR only under __GNUC__ >= 3, and clang-cl does not set
 * __GNUC__. picotls.h's own non-GNU branch defines PTLS_BUILD_ASSERT as 1; this is the same
 * for the _EXPR form, which PTLS_ASSERT_IS_ARRAY_EXPR (and so PTLS_ELEMENTSOF) uses under clang >= 10. */
#ifndef PTLS_BUILD_ASSERT_EXPR
#define PTLS_BUILD_ASSERT_EXPR(cond) 1
#endif

/* wincompat.h does `#define __attribute__(X)` unless __attribute__ is already a macro. Emptied, it
 * breaks clang's own intrinsic headers (mmintrin.h and the rest), which picotls/openssl.c reaches.
 * clang-cl understands __attribute__, so make the macro exist and expand to itself: the #ifndef
 * in wincompat.h then skips the empty definition and nothing else changes. */
#ifndef __attribute__
#define __attribute__ __attribute__
#endif
