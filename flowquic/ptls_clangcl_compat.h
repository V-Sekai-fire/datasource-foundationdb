/* picotls.h defines PTLS_BUILD_ASSERT_EXPR only under __GNUC__ >= 3, and clang-cl does not set
 * __GNUC__. picotls.h's own non-GNU branch defines PTLS_BUILD_ASSERT as 1; this is the same
 * for the _EXPR form, which PTLS_ASSERT_IS_ARRAY_EXPR (and so PTLS_ELEMENTSOF) uses under clang >= 10. */
#ifndef PTLS_BUILD_ASSERT_EXPR
#define PTLS_BUILD_ASSERT_EXPR(cond) 1
#endif
